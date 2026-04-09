# models.py
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, create_engine, Session


# ─────────────────────────────────────────────────────────────
# COMPONENT SETS  (e.g. "Button" — the variant group/module)
# ─────────────────────────────────────────────────────────────

class ComponentSet(SQLModel, table=True):
    __tablename__ = "component_sets"

    key: str = Field(primary_key=True)       # stable global key from Figma
    node_id: str = Field(unique=True)
    name: str
    description: str = ""

    # One ComponentSet → many Components (variants)
    components: List["Component"] = Relationship(back_populates="component_set")


# ─────────────────────────────────────────────────────────────
# COMPONENTS  (main component definitions — never instances)
# ─────────────────────────────────────────────────────────────

class Component(SQLModel, table=True):
    __tablename__ = "components"

    key: str = Field(primary_key=True)       # stable global key — used for /nodes fetch
    node_id: str = Field(unique=True)
    name: str
    description: str = ""
    remote: bool = Field(default=False)      # True = from a linked library file
    raw_node_json: Optional[str] = None      # full Figma node data with all properties
    screenshot: Optional[str] = None
    updated_at: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None

    # FK → ComponentSet (None if standalone component, not a variant)
    component_set_key: Optional[str] = Field(
        default=None, foreign_key="component_sets.key"
    )
    component_set: Optional[ComponentSet] = Relationship(back_populates="components")

    # One Component → many ComponentUsages (where it is instanced)
    usages: List["ComponentUsage"] = Relationship(back_populates="component")


# ─────────────────────────────────────────────────────────────
# PAGES  (each tab in the Figma file → a Next.js route)
# ─────────────────────────────────────────────────────────────

class Page(SQLModel, table=True):
    __tablename__ = "pages"

    page_id: str = Field(primary_key=True)   # Figma node ID e.g. "0:1"
    page_name: str
    order: int = 0                           # position of the tab in the file

    # One Page → many ComponentUsages
    usages: List["ComponentUsage"] = Relationship(back_populates="page")

    # One Page → many Frames
    frames: List["Frame"] = Relationship(back_populates="page")


# ─────────────────────────────────────────────────────────────
# FRAMES  (top-level artboards/screens on a page)
# ─────────────────────────────────────────────────────────────

class Frame(SQLModel, table=True):
    __tablename__ = "frames"

    frame_id: str = Field(primary_key=True)  # Figma node ID
    frame_name: str
    width: Optional[float] = None
    height: Optional[float] = None

    # FK → Page
    page_id: str = Field(foreign_key="pages.page_id")
    page: Optional[Page] = Relationship(back_populates="frames")

    # One Frame → many ComponentUsages
    usages: List["ComponentUsage"] = Relationship(back_populates="frame")


# ─────────────────────────────────────────────────────────────
# SECTION COMPONENTS (nested subframes promoted as components)
# ─────────────────────────────────────────────────────────────

class SectionComponent(SQLModel, table=True):
    __tablename__ = "section_components"

    node_id: str = Field(primary_key=True)  # Figma node ID for the section frame
    page_id: str = Field(foreign_key="pages.page_id")
    root_frame_id: str = Field(foreign_key="frames.frame_id")  # top-level frame
    parent_node_id: Optional[str] = Field(
        default=None, foreign_key="section_components.node_id"
    )
    depth: int = 0  # distance from the root frame
    order: int = 0  # sibling order within its parent
    name: str = ""
    width: Optional[float] = None
    height: Optional[float] = None
    raw_node_json: str = "{}"  # serialized Figma node for hydration
    screenshot: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# EXTRACTED IMAGES (embedded images from designs)
# ─────────────────────────────────────────────────────────────

class ExtractedImage(SQLModel, table=True):
    __tablename__ = "extracted_images"

    id: Optional[int] = Field(default=None, primary_key=True)
    image_ref: str = Field(index=True)  # Figma imageRef hash
    section_node_id: str = Field(foreign_key="section_components.node_id")  # parent section
    node_id: str  # specific node containing the image
    node_name: str = ""  # name of the node with the image
    node_path: str = ""  # path like "Hero/Background/Image"
    local_path: Optional[str] = None  # path to downloaded image file
    scale_mode: str = "FILL"  # FILL, FIT, CROP, TILE


# ─────────────────────────────────────────────────────────────
# COMPONENT USAGES  (junction: which component is used where)
# ─────────────────────────────────────────────────────────────

class ComponentUsage(SQLModel, table=True):
    __tablename__ = "component_usages"

    id: Optional[int] = Field(default=None, primary_key=True)
    instance_node_id: str = Field(unique=True)  # the INSTANCE node ID in the tree

    # FK → Component (the definition being instanced)
    component_key: str = Field(foreign_key="components.key")
    component: Optional[Component] = Relationship(back_populates="usages")

    # FK → Page
    page_id: str = Field(foreign_key="pages.page_id")
    page: Optional[Page] = Relationship(back_populates="usages")

    # FK → Frame (the top-level screen containing this instance)
    frame_id: Optional[str] = Field(default=None, foreign_key="frames.frame_id")
    frame: Optional[Frame] = Relationship(back_populates="usages")


# ─────────────────────────────────────────────────────────────
# VARIABLES  (design tokens — Enterprise only)
# ─────────────────────────────────────────────────────────────

class VariableCollection(SQLModel, table=True):
    __tablename__ = "variable_collections"

    collection_id: str = Field(primary_key=True)  # Figma collection ID
    name: str
    default_mode_id: str
    modes_json: str = "[]"   # JSON array of {modeId, name}
    remote: bool = False

    variables: List["Variable"] = Relationship(back_populates="collection")


class Variable(SQLModel, table=True):
    __tablename__ = "variables"

    variable_id: str = Field(primary_key=True)  # Figma variable ID
    name: str
    resolved_type: str           # BOOLEAN | FLOAT | STRING | COLOR
    values_by_mode_json: str = "{}"  # JSON map of {modeId: value}
    scopes_json: str = "[]"          # JSON array of scopes e.g. ["FILL_COLOR"]
    code_syntax_json: str = "{}"     # JSON map of {WEB: "...", ANDROID: "..."}
    remote: bool = False

    # FK → VariableCollection
    collection_id: str = Field(foreign_key="variable_collections.collection_id")
    collection: Optional[VariableCollection] = Relationship(back_populates="variables")


# ─────────────────────────────────────────────────────────────
# ENGINE & TABLE CREATION
# ─────────────────────────────────────────────────────────────
# Note: Database creation is now handled by db.manager.DatabaseManager
# Use get_project_session(project_id) to get a session for a project database