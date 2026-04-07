import json
import os
from pathlib import Path
from typing import Any
import time
from io import BytesIO

import requests
from PIL import Image
from sqlmodel import select, delete

from db.migration import (
    Component,
    ComponentSet,
    ComponentUsage,
    ExtractedImage,
    Frame,
    Page,
    SectionComponent,
    Variable,
    VariableCollection,
    create_db_and_tables,
)


class FigmaConnection:
    def __init__(
        self,
        figma_token: str,
        figma_project_key: str,
        batch_size: int = 50,
        db_path: str = "figma.db",
        start_canvas_name: str | None = "Delivery",
        fetch_screenshots: bool = True,
    ):
        self.figma_token = figma_token
        self.figma_project_key = figma_project_key
        self.batch_size = batch_size
        self.session = create_db_and_tables(db_path)
        self.data: dict[str, Any] | None = None
        self.images_map: dict[str, str] = {}  # imageRef -> URL mapping
        self.component_keys_by_node_id: dict[str, str] = {}
        self.debug = os.getenv("DEV", "").lower() in {"1", "true", "yes"}
        self.start_canvas_name = start_canvas_name
        self.fetch_screenshots = fetch_screenshots
        self.figma_screenshots_dir = Path("assets") / "figma_screenshots"
        self.figma_screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.figma_images_dir = Path("assets") / "figma_images"
        self.figma_images_dir.mkdir(parents=True, exist_ok=True)
        self.image_batch_size = 5  # Smaller batches to avoid overwhelming Figma API
        self.image_rate_limit_seconds = 1.0  # Longer delays between batches
        self.image_max_retries = 5
        self.section_max_depth = 1  # Only capture direct children of frames as sections
        self.min_component_width = 100  # Skip components smaller than this
        self.min_component_height = 100

    BASE_FIGMA_URL = "https://api.figma.com/v1"
    # Only capture FRAME and SECTION nodes as components, not GROUP (too granular)
    SECTION_FRAME_TYPES = {"FRAME", "SECTION"}

    def _debug(self, message: str, payload: dict[str, Any] | None = None) -> None:
        if not self.debug:
            return
        if payload is None:
            print(f"[DEBUG] {message}")
        else:
            print(f"[DEBUG] {message}: {payload}")

    def get_developer_variables(self) -> dict:
        # TODO: figure out why this is not working, even though the account is a paid one
        url = f"{self.BASE_FIGMA_URL}/files/{self.figma_project_key}/variables/local"
        headers = {"X-Figma-Token": self.figma_token}

        response = requests.get(url, headers=headers)

        if response.status_code == 403:
            raise PermissionError(
                "Access denied. Ensure your token has 'file_variables:read' scope "
                "and you are a full member of an Enterprise org."
            )

        if response.status_code == 404:
            raise ValueError(f"File '{self.figma_project_key}' not found.")

        if response.status_code != 200:
            raise RuntimeError(
                f"Figma API error {response.status_code}: {response.text}"
            )

        data = response.json()

        if data.get("err"):
            raise RuntimeError(f"The Figma API raised this error: {data}")

        meta = data.get("meta", {})

        variables = meta.get("variables", {})
        variable_collections = meta.get("variableCollections", {})

        print("\n=== Figma Variables ===")
        print(f"Variables: {variables}")
        print(f"Variable Collections: {variable_collections}")

        payload = {
            "variables": variables,
            "variable_collections": variable_collections,
        }

        self._persist_variables(payload)

        return payload

    def get_file(self) -> dict:
        # Request with geometry=paths to ensure we get image data
        # and plugin_data + images to get embedded image URLs
        params = {
            "geometry": "paths",
            "plugin_data": "shared"
        }
        response = requests.get(
            f"{self.BASE_FIGMA_URL}/files/{self.figma_project_key}",
            headers={"X-Figma-Token": self.figma_token},
            params=params
        )

        response.raise_for_status()
        data = response.json()
        self.data = data
        # Store images map for embedded image downloads
        self.images_map = data.get("images", {})
        if self.images_map:
            print(f"Found {len(self.images_map)} image assets in file")
            if self.debug:
                print(f"  Sample imageRefs: {list(self.images_map.keys())[:3]}")
        else:
            print("⚠️  No images map in file response - embedded images may not download")
        self._persist_file_contents()
        return data

    def _persist_file_contents(self) -> None:
        if not self.data:
            raise ValueError("No Figma data loaded. Call get_file() first.")

        # Clear old section components to avoid stale data
        print("Clearing old section components...")
        self.session.exec(delete(SectionComponent))
        self.session.commit()

        self._persist_component_sets()
        self._persist_components()
        self._enrich_components_from_tree()
        self._persist_pages_frames_and_usages()
        
        # Show count after processing
        sections_count = len(self.session.exec(select(SectionComponent)).all())
        components_enriched = len([c for c in self.session.exec(select(Component)).all() if c.raw_node_json])
        print(f"\n✓ Processed {sections_count} section components")
        print(f"✓ Enriched {components_enriched} components with full node data")
        
        if self.fetch_screenshots:
            self._persist_section_component_screenshots()
            self._persist_component_screenshots()
            self._extract_and_download_embedded_images()
        else:
            print("Skipping screenshot downloads (fetch_screenshots=False)")

    def _persist_component_sets(self) -> None:
        assert self.data is not None
        component_sets = self.data.get("componentSets", {})

        for node_id, payload in component_sets.items():
            key = payload.get("key")
            if not key:
                continue

            component_set = self.session.get(ComponentSet, key)
            if component_set is None:
                component_set = ComponentSet(
                    key=key,
                    node_id=node_id,
                    name=payload.get("name", ""),
                    description=payload.get("description", "") or "",
                )
                self._debug(
                    "ComponentSet created",
                    {
                        "key": key,
                        "node_id": node_id,
                        "name": component_set.name,
                    },
                )
            else:
                component_set.node_id = node_id
                component_set.name = payload.get("name", component_set.name)
                component_set.description = payload.get(
                    "description", component_set.description
                ) or ""
                self._debug(
                    "ComponentSet updated",
                    {
                        "key": key,
                        "node_id": node_id,
                        "name": component_set.name,
                    },
                )

            self.session.add(component_set)

        self.session.commit()

    def _persist_components(self) -> None:
        """Extract and store real Figma components from the file."""
        assert self.data is not None
        
        # Clear the mapping before populating
        self.component_keys_by_node_id.clear()
        
        components = self.data.get("components", {})
        
        for node_id, payload in components.items():
            key = payload.get("key")
            if not key:
                continue
            
            # Map node_id to key for instance resolution
            self.component_keys_by_node_id[node_id] = key
            
            component_set_key = payload.get("componentSetId")
            
            component = self.session.get(Component, key)
            if component is None:
                component = Component(
                    key=key,
                    node_id=node_id,
                    name=payload.get("name", ""),
                    description=payload.get("description", "") or "",
                    remote=False,
                    raw_node_json=None,
                    screenshot=None,
                    component_set_key=component_set_key,
                    width=None,
                    height=None,
                )
                self._debug(
                    "Component created",
                    {
                        "key": key,
                        "node_id": node_id,
                        "name": component.name,
                    },
                )
            else:
                component.node_id = node_id
                component.name = payload.get("name", component.name)
                component.description = payload.get("description", component.description) or ""
                component.component_set_key = component_set_key
                self._debug(
                    "Component updated",
                    {
                        "key": key,
                        "node_id": node_id,
                        "name": component.name,
                    },
                )
            
            self.session.add(component)
        
        self.session.commit()


    def _persist_pages_frames_and_usages(self) -> None:
        assert self.data is not None
        document = self.data.get("document", {})
        pages = [n for n in document.get("children", []) if n.get("type") == "CANVAS"]

        print(f"\n=== Canvas Processing ===\nTotal canvases in file: {len(pages)}")
        for p in pages:
            print(f"  - {p.get('name', 'Unnamed')}")

        if self.start_canvas_name:
            target_pages = [
                page
                for page in pages
                if page.get("name", "").strip().lower()
                == self.start_canvas_name.strip().lower()
            ]
            if not target_pages:
                print(f"⚠ Canvas '{self.start_canvas_name}' not found. Processing ALL canvases.")
                target_pages = pages
            else:
                print(f"✓ Processing only canvas: '{self.start_canvas_name}'")
        else:
            print("⚠ No canvas specified. Processing ALL canvases.")
            target_pages = pages
        
        print(f"Total canvases to process: {len(target_pages)}\n")

        for order, page in enumerate(target_pages):
            canvas_name = page.get("name", "Unnamed")
            print(f"Processing canvas: '{canvas_name}'")
            
            if self.start_canvas_name and page not in pages:
                # Should not happen, but guard to avoid inconsistent state.
                continue

            if self.start_canvas_name:
                frames = [
                    f
                    for f in page.get("children", []) or []
                    if f.get("id") and f.get("type") in {"FRAME", "COMPONENT", "SECTION"}
                ]
                print(f"  Found {len(frames)} top-level frames in '{canvas_name}' (each will be a separate page)")
                for frame_order, frame in enumerate(frames):
                    frame_name = frame.get("name", "Unnamed")
                    print(f"  Processing frame {frame_order + 1}/{len(frames)}: '{frame_name}'")
                    page_model = self._upsert_page(frame.get("id"), frame_name, frame_order)
                    self.session.add(page_model)
                    self._persist_frame(page_model.page_id, frame)
            else:
                page_model = self._upsert_page(page.get("id"), canvas_name, order)
                self.session.add(page_model)

                frames = page.get("children", []) or []
                print(f"  Found {len(frames)} frames in '{canvas_name}'")
                for frame in frames:
                    self._persist_frame(page_model.page_id, frame)

        self.session.commit()

    def _upsert_page(self, page_id: str | None, page_name: str, order: int) -> Page:
        if not page_id:
            raise ValueError("Encountered a page/frame without an id while persisting")

        page_model = self.session.get(Page, page_id)
        if page_model is None:
            page_model = Page(page_id=page_id, page_name=page_name, order=order)
            self._debug("Page created", {"page_id": page_id, "name": page_model.page_name})
        else:
            page_model.page_name = page_name or page_model.page_name
            page_model.order = order
            self._debug("Page updated", {"page_id": page_id, "name": page_model.page_name})

        return page_model

    def _persist_frame(self, page_id: str, frame: dict[str, Any]) -> None:
        frame_id = frame.get("id")
        frame_type = frame.get("type")

        if not frame_id or frame_type not in {"FRAME", "COMPONENT", "SECTION"}:
            # Still recurse to catch nested instances
            for child in frame.get("children", []) or []:
                self._record_component_usages(page_id, None, child)
            return

        bbox = frame.get("absoluteBoundingBox") or {}
        width = bbox.get("width")
        height = bbox.get("height")

        frame_model = self.session.get(Frame, frame_id)
        if frame_model is None:
            frame_model = Frame(
                frame_id=frame_id,
                frame_name=frame.get("name", ""),
                width=width,
                height=height,
                page_id=page_id,
            )
            self._debug(
                "Frame created",
                {"frame_id": frame_id, "name": frame_model.frame_name, "page_id": page_id},
            )
        else:
            frame_model.frame_name = frame.get("name", frame_model.frame_name)
            frame_model.width = width or frame_model.width
            frame_model.height = height or frame_model.height
            frame_model.page_id = page_id
            self._debug(
                "Frame updated",
                {"frame_id": frame_id, "name": frame_model.frame_name, "page_id": page_id},
            )

        self.session.add(frame_model)

        self._persist_section_components(
            page_id,
            frame_model.frame_id,
            frame,
            depth=0,
            parent_section_id=None,
        )
        self._record_component_usages(page_id, frame_id, frame)

    def _sanitize_asset_name(self, raw_name: str, fallback: str) -> str:
        candidate = (raw_name or "").strip()
        candidate = candidate[:80]
        candidate = "".join(c for c in candidate if c.isalnum() or c in {" ", "-", "_", "#"}).strip()
        if not candidate:
            candidate = fallback
        return candidate

    def _persist_section_component_screenshots(self) -> None:
        sections = self.session.exec(select(SectionComponent)).all()
        if not sections:
            return

        # Print statistics about sections
        depth_counts = {}
        for section in sections:
            depth_counts[section.depth] = depth_counts.get(section.depth, 0) + 1
        print(f"\n=== Section Component Statistics ===")
        print(f"Total sections: {len(sections)}")
        for depth in sorted(depth_counts.keys()):
            print(f"  Depth {depth}: {depth_counts[depth]} components")
        print("=" * 40)

        node_ids_requiring_images: list[str] = []
        targets: dict[str, tuple[SectionComponent, Path]] = {}

        for section in sections:
            existing_path = Path(section.screenshot) if section.screenshot else None
            if existing_path and existing_path.exists():
                continue

            safe_name = self._sanitize_asset_name(
                section.name, section.node_id.replace(":", "_")
            )
            filename = f"section_{safe_name}_{section.node_id.replace(':', '_')}.png"
            screenshot_path = self.figma_screenshots_dir / filename

            node_ids_requiring_images.append(section.node_id)
            targets[section.node_id] = (section, screenshot_path)

        if not node_ids_requiring_images:
            return

        print(f"\nDownloading screenshots for {len(node_ids_requiring_images)} section components...")
        screenshot_bytes_map = self._fetch_component_screenshots(node_ids_requiring_images)

        saved_count = 0
        for node_id, (section, screenshot_path) in targets.items():
            screenshot_bytes = screenshot_bytes_map.get(node_id)
            if screenshot_bytes is None:
                self._debug(
                    "Missing screenshot bytes for section",
                    {"node_id": node_id, "name": section.name},
                )
                continue

            # Process image to add white background if transparent
            processed_bytes = self._add_white_background(screenshot_bytes)
            screenshot_path.write_bytes(processed_bytes)
            section.screenshot = str(screenshot_path)
            self.session.add(section)
            saved_count += 1

        self.session.commit()
        print(f"✓ Saved {saved_count} section component screenshots")

    def _persist_component_screenshots(self) -> None:
        """Fetch and save screenshots for real Figma components."""
        components = self.session.exec(select(Component)).all()
        if not components:
            return

        node_ids_requiring_images: list[str] = []
        targets: dict[str, tuple[Component, Path]] = {}

        for component in components:
            existing_path = Path(component.screenshot) if component.screenshot else None
            if existing_path and existing_path.exists():
                continue

            safe_name = self._sanitize_asset_name(
                component.name, component.node_id.replace(":", "_")
            )
            filename = f"component_{safe_name}_{component.node_id.replace(':', '_')}.png"
            screenshot_path = self.figma_screenshots_dir / filename

            node_ids_requiring_images.append(component.node_id)
            targets[component.node_id] = (component, screenshot_path)

        if not node_ids_requiring_images:
            return

        print(f"Downloading screenshots for {len(node_ids_requiring_images)} components...")
        screenshot_bytes_map = self._fetch_component_screenshots(node_ids_requiring_images)

        saved_count = 0
        for node_id, (component, screenshot_path) in targets.items():
            screenshot_bytes = screenshot_bytes_map.get(node_id)
            if screenshot_bytes is None:
                self._debug(
                    "Missing screenshot bytes for component",
                    {"node_id": node_id, "name": component.name},
                )
                continue

            # Process image to add white background if transparent
            processed_bytes = self._add_white_background(screenshot_bytes)
            screenshot_path.write_bytes(processed_bytes)
            component.screenshot = str(screenshot_path)
            self.session.add(component)
            saved_count += 1

        self.session.commit()
        print(f"✓ Saved {saved_count} component screenshots")

    def _persist_section_components(
        self,
        page_id: str,
        root_frame_id: str,
        node: dict[str, Any],
        depth: int,
        parent_section_id: str | None,
    ) -> None:
        """
        Extract section components from a frame.
        With section_max_depth=1, only direct children of frames are captured as sections.
        This provides semantic page sections (Hero, Features, Footer) without thousands of nested elements.
        """
        children = node.get("children") or []
        if not children:
            return

        # If we're at depth 0 (the frame itself), process its direct children
        # If we're already at depth >= section_max_depth, stop processing
        if depth >= self.section_max_depth:
            return

        for order, child in enumerate(children):
            node_id = child.get("id")
            node_type = child.get("type")
            
            if not node_id or not node_type:
                continue

            # Skip component instances (tracked separately)
            if node_type == "INSTANCE" and child.get("componentId"):
                continue
            
            # Only capture FRAME and SECTION types as section components
            if node_type not in self.SECTION_FRAME_TYPES:
                continue
            
            bbox = child.get("absoluteBoundingBox") or {}
            width = bbox.get("width")
            height = bbox.get("height")
            
            # Skip invisible nodes
            visible = child.get("visible", True)
            if not visible:
                self._debug(
                    "Skipping invisible section",
                    {"node_id": node_id, "name": child.get("name", ""), "type": node_type},
                )
                continue
            
            # Skip zero-opacity nodes
            opacity = child.get("opacity", 1.0)
            if opacity <= 0:
                self._debug(
                    "Skipping zero-opacity section",
                    {"node_id": node_id, "name": child.get("name", ""), "type": node_type},
                )
                continue
            
            # Skip mask nodes
            if child.get("isMask", False):
                self._debug(
                    "Skipping mask section",
                    {"node_id": node_id, "name": child.get("name", ""), "type": node_type},
                )
                continue
            
            # Skip nodes with invalid dimensions
            if not width or not height or width <= 0 or height <= 0:
                self._debug(
                    "Skipping zero-dimension section",
                    {"node_id": node_id, "name": child.get("name", ""), "type": node_type, "size": f"{width}x{height}"},
                )
                continue
            
            # Skip tiny components
            if width < self.min_component_width or height < self.min_component_height:
                self._debug(
                    "Skipping small section",
                    {"node_id": node_id, "name": child.get("name", ""), "type": node_type, "size": f"{width}x{height}"},
                )
                continue
            
            # Create or update the section component
            raw_json = json.dumps(child)
            section_component = self.session.get(SectionComponent, node_id)
            
            if section_component is None:
                section_component = SectionComponent(
                    node_id=node_id,
                    page_id=page_id,
                    root_frame_id=root_frame_id,
                    parent_node_id=parent_section_id,
                    depth=depth + 1,
                    order=order,
                    name=child.get("name", ""),
                    width=width,
                    height=height,
                    raw_node_json=raw_json,
                )
                print(f"  → Creating section: '{child.get('name', '')}' ({node_type}, {width:.0f}x{height:.0f}px)")
                self._debug(
                    "Section component created",
                    {
                        "node_id": node_id,
                        "name": section_component.name,
                        "depth": depth + 1,
                        "type": node_type,
                    },
                )
            else:
                section_component.page_id = page_id
                section_component.root_frame_id = root_frame_id
                section_component.parent_node_id = parent_section_id
                section_component.depth = depth + 1
                section_component.order = order
                section_component.name = child.get("name", section_component.name)
                section_component.width = width or section_component.width
                section_component.height = height or section_component.height
                section_component.raw_node_json = raw_json or section_component.raw_node_json
                self._debug(
                    "Section component updated",
                    {
                        "node_id": node_id,
                        "name": section_component.name,
                        "depth": depth + 1,
                        "type": node_type,
                    },
                )

            self.session.add(section_component)

    def _enrich_components_from_tree(self) -> None:
        """Traverse the document tree to find COMPONENT nodes and enrich them with full data."""
        assert self.data is not None
        
        print("\n=== Enriching components with full node data ===")
        document = self.data.get("document", {})
        
        # Traverse the entire document tree
        self._find_and_enrich_component_nodes(document)
        
        self.session.commit()
    
    def _find_and_enrich_component_nodes(self, node: dict[str, Any]) -> None:
        """Recursively traverse the node tree to find and enrich COMPONENT nodes."""
        node_type = node.get("type")
        node_id = node.get("id")
        
        # If this is a COMPONENT node, enrich it
        if node_type == "COMPONENT" and node_id:
            key = self.component_keys_by_node_id.get(node_id)
            if key:
                component = self.session.get(Component, key)
                if component:
                    # Store the full node JSON with all properties
                    component.raw_node_json = json.dumps(node)
                    
                    # Extract dimensional data
                    bbox = node.get("absoluteBoundingBox") or {}
                    component.width = bbox.get("width")
                    component.height = bbox.get("height")
                    
                    self.session.add(component)
                    print(f"  → Enriched component: '{component.name}' ({component.width}x{component.height}px)")
                    self._debug(
                        "Component enriched with full node data",
                        {
                            "key": key,
                            "node_id": node_id,
                            "name": component.name,
                            "has_children": len(node.get("children", [])) > 0,
                            "has_styles": bool(node.get("styles")),
                            "has_fills": bool(node.get("fills")),
                        },
                    )
        
        # Recurse through all children
        for child in node.get("children", []) or []:
            self._find_and_enrich_component_nodes(child)

            
    def _record_component_usages(
        self, page_id: str, frame_id: str | None, node: dict[str, Any]
    ) -> None:
        node_type = node.get("type")
        if node_type == "INSTANCE" and node.get("componentId"):
            component_key = self.component_keys_by_node_id.get(node["componentId"])
            if component_key:
                usage = self.session.exec(
                    select(ComponentUsage).where(
                        ComponentUsage.instance_node_id == node["id"]
                    )
                ).first()

                if usage is None:
                    usage = ComponentUsage(instance_node_id=node["id"])

                usage.component_key = component_key
                usage.page_id = page_id
                usage.frame_id = frame_id

                self.session.add(usage)
                self._debug(
                    "Component usage recorded",
                    {
                        "instance_node_id": node["id"],
                        "component_key": component_key,
                        "page_id": page_id,
                        "frame_id": frame_id,
                    },
                )

        for child in node.get("children", []) or []:
            self._record_component_usages(page_id, frame_id, child)

    def _persist_variables(self, payload: dict[str, Any]) -> None:
        collections = payload.get("variable_collections") or []
        for collection in collections:
            collection_id = collection.get("id")
            if not collection_id:
                continue

            modes_json = json.dumps(collection.get("modes", []))

            record = self.session.get(VariableCollection, collection_id)
            if record is None:
                record = VariableCollection(
                    collection_id=collection_id,
                    name=collection.get("name", ""),
                    default_mode_id=collection.get("defaultModeId", ""),
                    modes_json=modes_json,
                    remote=bool(collection.get("remote", False)),
                )
                self._debug(
                    "Variable collection created",
                    {"collection_id": collection_id, "name": record.name},
                )
            else:
                record.name = collection.get("name", record.name)
                record.default_mode_id = collection.get(
                    "defaultModeId", record.default_mode_id
                )
                record.modes_json = modes_json or record.modes_json
                record.remote = bool(collection.get("remote", record.remote))
                self._debug(
                    "Variable collection updated",
                    {"collection_id": collection_id, "name": record.name},
                )

            self.session.add(record)

        variables = payload.get("variables") or []
        for variable in variables:
            variable_id = variable.get("id")
            if not variable_id:
                continue

            values_by_mode = json.dumps(variable.get("valuesByMode", {}))
            scopes_json = json.dumps(variable.get("scopes", []))
            code_syntax_json = json.dumps(variable.get("codeSyntax", {}))

            record = self.session.get(Variable, variable_id)
            if record is None:
                record = Variable(
                    variable_id=variable_id,
                    name=variable.get("name", ""),
                    resolved_type=variable.get("resolvedType", ""),
                    values_by_mode_json=values_by_mode,
                    scopes_json=scopes_json,
                    code_syntax_json=code_syntax_json,
                    remote=bool(variable.get("remote", False)),
                    collection_id=variable.get("variableCollectionId", ""),
                )
                self._debug(
                    "Variable created",
                    {
                        "variable_id": variable_id,
                        "name": record.name,
                        "collection_id": record.collection_id,
                    },
                )
            else:
                record.name = variable.get("name", record.name)
                record.resolved_type = variable.get(
                    "resolvedType", record.resolved_type
                )
                record.values_by_mode_json = values_by_mode or record.values_by_mode_json
                record.scopes_json = scopes_json or record.scopes_json
                record.code_syntax_json = code_syntax_json or record.code_syntax_json
                record.remote = bool(variable.get("remote", record.remote))
                record.collection_id = variable.get(
                    "variableCollectionId", record.collection_id
                )
                self._debug(
                    "Variable updated",
                    {
                        "variable_id": variable_id,
                        "name": record.name,
                        "collection_id": record.collection_id,
                    },
                )

            self.session.add(record)

        self.session.commit()

    def _fetch_component_screenshots(self, node_ids: list[str]) -> dict[str, bytes]:
        results: dict[str, bytes] = {}
        if not node_ids:
            return results

        total_batches = (len(node_ids) + self.image_batch_size - 1) // self.image_batch_size
        for batch_idx, start in enumerate(range(0, len(node_ids), self.image_batch_size), 1):
            batch = node_ids[start : start + self.image_batch_size]
            print(f"  Fetching batch {batch_idx}/{total_batches} ({len(batch)} images)...", end="", flush=True)
            batch_results = self._request_component_images(batch)
            results.update(batch_results)
            print(f" ✓ ({len(batch_results)} received)")
            if batch_idx < total_batches:
                time.sleep(self.image_rate_limit_seconds)

        return results

    def _request_component_images(self, node_ids: list[str]) -> dict[str, bytes]:
        url = f"{self.BASE_FIGMA_URL}/images/{self.figma_project_key}"
        headers = {"X-Figma-Token": self.figma_token}
        ids_param = ",".join(node_ids)
        # Use PNG with white background so components without fills are visible
        # This ensures text and elements are always readable
        params = {
            "ids": ids_param,
            "format": "png",
            "scale": 2,
            "use_absolute_bounds": "true",
        }

        attempt = 0
        while attempt <= self.image_max_retries:
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 429:
                wait_time = self.image_rate_limit_seconds * (2**attempt)
                print(
                    "Need to give Figma some time to breathe, so we don't break their limits..."
                )
                time.sleep(wait_time)
                attempt += 1
                continue

            if response.status_code == 403:
                raise PermissionError(
                    "Access denied. Ensure your token has 'file_images:read' scope "
                    "and you are a full member of an Enterprise org."
                )

            if response.status_code == 404:
                raise ValueError(f"File '{self.figma_project_key}' not found.")

            if response.status_code != 200:
                raise RuntimeError(
                    f"Figma API error {response.status_code}: {response.text}"
                )

            images_payload = response.json().get("images", {})
            missing = [node_id for node_id in node_ids if not images_payload.get(node_id)]
            if missing:
                print(f"\n  ⚠ Warning: Figma did not return image URLs for {len(missing)} node(s): {', '.join(missing[:5])}")
                if len(missing) > 5:
                    print(f"    ... and {len(missing) - 5} more")
                print("  Continuing with nodes that have valid image URLs...")

            bytes_map: dict[str, bytes] = {}
            for node_id, image_url in images_payload.items():
                if not image_url:
                    # Skip null/empty URLs
                    continue
                try:
                    bytes_map[node_id] = self._download_image_bytes(image_url)
                except Exception as e:
                    print(f"\n  ⚠ Failed to download {node_id}: {str(e)[:50]}")
                    # Continue with other images instead of failing completely
                    continue

            return bytes_map

        raise RuntimeError("Exceeded retries while fetching component screenshots from Figma")

    def _download_image_bytes(self, image_url: str) -> bytes:
        attempt = 0
        while attempt <= self.image_max_retries:
            try:
                response = requests.get(image_url, timeout=30)
                if response.status_code == 429:
                    wait_time = self.image_rate_limit_seconds * (2**attempt)
                    time.sleep(wait_time)
                    attempt += 1
                    continue

                if response.status_code == 404:
                    raise ValueError("Screenshot asset no longer available at provided URL")

                if response.status_code != 200:
                    raise RuntimeError(
                        f"Figma image download failed with status {response.status_code}: {response.text}"
                    )

                return response.content
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                attempt += 1
                if attempt > self.image_max_retries:
                    raise RuntimeError(f"Failed to download image after {self.image_max_retries} retries: {e}")
                wait_time = self.image_rate_limit_seconds * (2**attempt)
                print(f" [retry {attempt}/{self.image_max_retries} after {wait_time}s]...", end="", flush=True)
                time.sleep(wait_time)
                continue

        raise RuntimeError("Exceeded retries while downloading component screenshot data")

    def _add_white_background(self, image_bytes: bytes) -> bytes:
        """Add white background to transparent PNGs to ensure visibility."""
        try:
            # Open the image
            img = Image.open(BytesIO(image_bytes))
            
            # If image has transparency (RGBA or P mode with transparency)
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                # Convert to RGBA if needed
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # Create white background
                background = Image.new('RGBA', img.size, (255, 255, 255, 255))
                
                # Composite image over white background
                background.paste(img, (0, 0), img)
                
                # Convert to RGB (remove alpha channel)
                img = background.convert('RGB')
            elif img.mode != 'RGB':
                # Convert other modes to RGB
                img = img.convert('RGB')
            
            # Save to bytes
            output = BytesIO()
            img.save(output, format='PNG', optimize=True)
            return output.getvalue()
        except Exception as e:
            # If processing fails, return original bytes
            self._debug(f"Failed to process image: {e}")
            return image_bytes

    def _extract_and_download_embedded_images(self) -> None:
        """
        Extract and download embedded images (photos, logos, etc.) from section components.
        This is different from section screenshots - these are actual images embedded in the design.
        """
        print("\n=== Extracting Embedded Images from Sections ===")
        
        sections = self.session.exec(select(SectionComponent)).all()
        if not sections:
            print("No sections to extract images from")
            return
        
        # Find all image fills in all sections
        image_data_list = []
        for section in sections:
            if not section.raw_node_json:
                continue
            
            try:
                node = json.loads(section.raw_node_json)
                images = self._find_image_fills_in_node(node, section.node_id, section.name)
                image_data_list.extend(images)
            except Exception as e:
                self._debug(f"Error parsing section {section.node_id}: {e}")
                continue
        
        if not image_data_list:
            print("No embedded images found in sections")
            return
        
        print(f"Found {len(image_data_list)} embedded images across {len(sections)} sections")
        
        # Debug: Show what data we have
        if self.debug and image_data_list:
            sample = image_data_list[0]
            print(f"  Sample image data:")
            print(f"    - image_ref: {sample.get('image_ref', 'None')[:50] if sample.get('image_ref') else 'None'}...")
            print(f"    - node_id: {sample.get('node_id', 'None')}")
            print(f"    - node_name: {sample.get('node_name', 'None')}")
        
        # Group by imageRef to get unique images
        images_by_ref = {}
        for img_data in image_data_list:
            ref = img_data["image_ref"]
            if ref and ref not in images_by_ref:
                images_by_ref[ref] = []
            if ref:
                images_by_ref[ref].append(img_data)
        
        print(f"Unique images to download: {len(images_by_ref)}")
        
        # Strategy: Try multiple methods to get the actual images
        # 1. Check images_map from file response
        # 2. Try API request for image fills
        # 3. Fall back to rendering the nodes containing the images
        
        print("  → Attempting to fetch original image files...")
        image_urls = {}
        
        # Method 1: Check pre-loaded images_map
        if self.images_map:
            for image_ref in images_by_ref.keys():
                if image_ref in self.images_map:
                    image_urls[image_ref] = self.images_map[image_ref]
            if image_urls:
                print(f"    Found {len(image_urls)} URLs in images_map")
        
        # Method 2: Try API request
        remaining_refs = [ref for ref in images_by_ref.keys() if ref not in image_urls]
        if remaining_refs:
            api_urls = self._request_image_fills_urls(remaining_refs)
            image_urls.update(api_urls)
        
        # If we got URLs, download the original images
        if image_urls:
            print(f"  → Downloading {len(image_urls)} original image files...")
            downloaded_count = 0
            
            for image_ref, image_url in image_urls.items():
                try:
                    image_bytes = self._download_image_bytes(image_url)
                    
                    # Save to disk
                    usages = images_by_ref[image_ref]
                    usage = usages[0]
                    safe_name = usage["node_name"].replace("/", "_").replace(":", "_")[:50]
                    safe_ref = image_ref[:20].replace("/", "_").replace(":", "_")
                    filename = f"image_{safe_name}_{safe_ref}.png"
                    image_path = self.figma_images_dir / filename
                    image_path.write_bytes(image_bytes)
                    
                    # Store in database for all usages
                    for usage in usages:
                        existing = self.session.exec(
                            select(ExtractedImage).where(
                                ExtractedImage.section_node_id == usage["section_node_id"],
                                ExtractedImage.node_id == usage["node_id"]
                            )
                        ).first()
                        
                        if existing:
                            existing.local_path = str(image_path)
                            existing.image_ref = image_ref
                            self.session.add(existing)
                        else:
                            extracted_img = ExtractedImage(
                                image_ref=image_ref,
                                section_node_id=usage["section_node_id"],
                                node_id=usage["node_id"],
                                node_name=usage["node_name"],
                                node_path=usage["node_path"],
                                local_path=str(image_path),
                                scale_mode=usage["scale_mode"]
                            )
                            self.session.add(extracted_img)
                    
                    downloaded_count += 1
                    if downloaded_count % 5 == 0:
                        print(f"    Downloaded {downloaded_count}/{len(image_urls)} images...")
                        
                except Exception as e:
                    if self.debug:
                        print(f"    ✗ Failed to download {image_ref[:20]}: {str(e)}")
                    continue
            
            self.session.commit()
            print(f"✓ Downloaded {downloaded_count} original images")
            
            # Report any that couldn't be downloaded
            remaining = len(images_by_ref) - len(image_urls)
            if remaining > 0:
                print(f"⚠️  {remaining} images had no downloadable URLs")
        
        else:
            # Method 3: Fall back to rendering nodes containing images
            print("  ⚠️  No direct image URLs available")
            print("  → Falling back to rendering image-containing nodes...")
            
            # Group by node_id for rendering
            images_by_node = {}
            for image_ref, usages in images_by_ref.items():
                for usage in usages:
                    node_id = usage["node_id"]
                    if node_id not in images_by_node:
                        images_by_node[node_id] = usage
            
            node_ids = list(images_by_node.keys())
            rendered_images = self._fetch_component_screenshots(node_ids)
            
            if rendered_images:
                print(f"  → Rendered {len(rendered_images)} image nodes")
                saved_count = 0
                
                for node_id, image_bytes in rendered_images.items():
                    try:
                        usage = images_by_node[node_id]
                        safe_name = usage["node_name"].replace("/", "_").replace(":", "_")[:50]
                        filename = f"rendered_{safe_name}_{node_id.replace(':', '_')}.png"
                        image_path = self.figma_images_dir / filename
                        
                        processed_bytes = self._add_white_background(image_bytes)
                        image_path.write_bytes(processed_bytes)
                        
                        existing = self.session.exec(
                            select(ExtractedImage).where(
                                ExtractedImage.section_node_id == usage["section_node_id"],
                                ExtractedImage.node_id == node_id
                            )
                        ).first()
                        
                        if existing:
                            existing.local_path = str(image_path)
                            self.session.add(existing)
                        else:
                            extracted_img = ExtractedImage(
                                image_ref=usage.get("image_ref"),
                                section_node_id=usage["section_node_id"],
                                node_id=node_id,
                                node_name=usage["node_name"],
                                node_path=usage["node_path"],
                                local_path=str(image_path),
                                scale_mode=usage["scale_mode"]
                            )
                            self.session.add(extracted_img)
                        
                        saved_count += 1
                    except Exception as e:
                        if self.debug:
                            print(f"    ✗ Failed to save {node_id}: {str(e)}")
                        continue
                
                self.session.commit()
                print(f"✓ Saved {saved_count} rendered images (containing original images)")
            else:
                print("  ✗ Could not download images via any method")
    
    def _find_image_fills_in_node(
        self, 
        node: dict[str, Any], 
        section_node_id: str,
        section_name: str,
        path: str = ""
    ) -> list[dict[str, Any]]:
        """
        Recursively find all IMAGE fills in a node tree.
        Returns list of dicts with image metadata.
        
        Strategy: Instead of trying to fetch imageRefs (which aren't valid node IDs),
        we'll render the actual nodes that contain image fills.
        """
        image_fills = []
        node_name = node.get("name", "")
        current_path = f"{path}/{node_name}" if path else node_name
        node_id = node.get("id", "")
        node_type = node.get("type", "")
        
        # Check fills for IMAGE type
        has_image_fill = False
        fills = node.get("fills", [])
        if isinstance(fills, list):
            for fill in fills:
                if fill.get("type") == "IMAGE":
                    has_image_fill = True
                    image_ref = fill.get("imageRef")
                    # Some images might have direct URLs instead of refs
                    direct_url = fill.get("url")
                    
                    # Store both the imageRef and the node_id that contains it
                    # We'll render the node_id instead of fetching the imageRef
                    if image_ref or direct_url or node_id:
                        image_fills.append({
                            "image_ref": image_ref,
                            "direct_url": direct_url,  # Might be None
                            "section_node_id": section_node_id,
                            "node_id": node_id,  # The node containing the image
                            "node_name": node_name,
                            "node_path": current_path,
                            "node_type": node_type,
                            "scale_mode": fill.get("scaleMode", "FILL"),
                            "has_image_fill": True  # Flag to render this node
                        })
        
        # Recurse through children
        children = node.get("children", [])
        if isinstance(children, list):
            for child in children:
                child_images = self._find_image_fills_in_node(
                    child, 
                    section_node_id,
                    section_name,
                    current_path
                )
                image_fills.extend(child_images)
        
        return image_fills
    
    def _request_image_fills_urls(self, image_refs: list[str]) -> dict[str, str]:
        """
        Request URLs for image fills by fetching the file with image export.
        
        The Figma API provides image URLs through a separate request that exports
        the image fills as downloadable assets.
        
        Args:
            image_refs: List of imageRef hashes from IMAGE fills
            
        Returns:
            Dict mapping imageRef -> download URL
        """
        if not image_refs:
            return {}
        
        print(f"    Requesting image fill URLs for {len(image_refs)} images...")
        
        # Use the /images endpoint with SVG format to get fill images
        # This is a workaround - request image fills as part of node exports
        url = f"{self.BASE_FIGMA_URL}/images/{self.figma_project_key}"
        headers = {"X-Figma-Token": self.figma_token}
        
        all_urls = {}
        
        # Try batch requests
        batch_size = 50
        for i in range(0, len(image_refs), batch_size):
            batch = image_refs[i:i + batch_size]
            
            # Format imageRefs with 'I' prefix as Figma expects for image fills
            # ImageRefs need to be prefixed to be recognized as fill references
            formatted_ids = ",".join([f"I{ref}" if not ref.startswith("I") else ref for ref in batch])
            
            params = {
                "ids": formatted_ids,
                "format": "png",
                "svg_include_id": "true"
            }
            
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                
                if self.debug:
                    print(f"    Batch {i//batch_size + 1}: Status {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    images = data.get("images", {})
                    
                    # Map back without the 'I' prefix
                    for key, img_url in images.items():
                        if img_url:
                            # Remove 'I' prefix if present
                            clean_key = key[1:] if key.startswith("I") else key
                            all_urls[clean_key] = img_url
                    
                    if self.debug:
                        print(f"    Got {len(images)} URLs from batch")
                        
                elif response.status_code == 400:
                    if self.debug:
                        print(f"    400 error - imageRefs not recognized as exportable IDs")
                    # ImageRefs can't be exported directly
                    break
                    
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                if self.debug:
                    print(f"    Error in batch {i//batch_size + 1}: {e}")
                continue
        
        return all_urls

    def hydrate_components(self):
        sections = self.session.exec(select(SectionComponent)).all()
        if not sections:
            print("No section components available to hydrate. Run get_file() first.")
            return

        for section in sections:
            node_id = section.node_id
            print(f"Hydration placeholder for section '{section.name}' ({node_id})")

            response = requests.get(
                f"{self.BASE_FIGMA_URL}/files/{self.figma_project_key}?node-id={node_id}",
                headers={"X-Figma-Token": self.figma_token},
            )

            response.raise_for_status()

            data = response.json()

            print(data, "\n\n\n")

    def extract_text_content(node: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Recursively extract all text content from a Figma node.
        
        Args:
            node: Figma node JSON
            
        Returns:
            List of dicts with 'text', 'name', and 'path' keys
        """
        text_nodes = []
        
        def traverse(current_node: Dict[str, Any], path: str = "") -> None:
            node_type = current_node.get("type")
            node_name = current_node.get("name", "")
            current_path = f"{path}/{node_name}" if path else node_name
            
            # Text nodes contain the actual text content
            if node_type == "TEXT":
                characters = current_node.get("characters", "")
                if characters:
                    text_nodes.append({
                        "text": characters,
                        "name": node_name,
                        "path": current_path,
                        "id": current_node.get("id", "")
                    })
            
            # Recurse through children
            children = current_node.get("children", [])
            for child in children:
                traverse(child, current_path)
        
        traverse(node)
        return text_nodes


    def extract_image_fills(node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Recursively extract all image fills from a Figma node.
        
        Args:
            node: Figma node JSON
            
        Returns:
            List of dicts with image fill information
        """
        image_fills = []
        
        def traverse(current_node: Dict[str, Any], path: str = "") -> None:
            node_name = current_node.get("name", "")
            current_path = f"{path}/{node_name}" if path else node_name
            
            # Check fills for images
            fills = current_node.get("fills", [])
            for fill in fills:
                if fill.get("type") == "IMAGE":
                    image_ref = fill.get("imageRef")
                    if image_ref:
                        image_fills.append({
                            "imageRef": image_ref,
                            "name": node_name,
                            "path": current_path,
                            "scaleMode": fill.get("scaleMode", "FILL"),
                            "nodeId": current_node.get("id", "")
                        })
            
            # Recurse through children
            children = current_node.get("children", [])
            for child in children:
                traverse(child, current_path)
        
        traverse(node)
        return image_fills


    def parse_figma_node(self) -> Optional[Dict[str, Any]]:
        """
        Parse raw Figma node JSON string.
        
        Args:
            raw_node_json: JSON string from database
            
        Returns:
            Parsed JSON dict or None if parsing fails
        """
        if not raw_node_json:
            return None
        
        try:
            return json.loads(raw_node_json)
        except json.JSONDecodeError as e:
            print(f"Error parsing Figma JSON: {e}")
            return None


    def extract_component_data(self) -> Dict[str, Any]:
        """
        Extract all relevant data from a Figma component node.
        
        Args:
            raw_node_json: Raw JSON string from database
            
        Returns:
            Dictionary with extracted text and images
        """
        node = parse_figma_node(raw_node_json)
        if not node:
            return {"texts": [], "images": []}
        
        texts = extract_text_content(node)
        images = extract_image_fills(node)
        
        return {
            "texts": texts,
            "images": images,
            "node_name": node.get("name", ""),
            "node_id": node.get("id", "")
        }