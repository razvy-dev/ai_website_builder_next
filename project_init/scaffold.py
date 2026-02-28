from pathlib import Path


def read_template(relative_path: str) -> str:
    """Read a template file from assets/templates."""
    template_dir = Path(__file__).resolve().parent.parent / "assets" / "templates"
    return (template_dir / relative_path).read_text()


def create_sanity_client(output_dir: Path) -> None:
    """Create Sanity client with stega for Visual Editing."""
    src_dir = output_dir / "frontend" / "src" / "sanity" / "lib"
    src_dir.mkdir(parents=True, exist_ok=True)

    (src_dir / "client.ts").write_text(read_template("sanity/client.ts"))
    print(f"  Created: {src_dir / 'client.ts'}")

    (src_dir / "token.ts").write_text(read_template("sanity/token.ts"))
    print(f"  Created: {src_dir / 'token.ts'}")


def create_live_mode(output_dir: Path) -> None:
    """Create Sanity Live configuration."""
    src_dir = output_dir / "frontend" / "src" / "sanity" / "lib"
    src_dir.mkdir(parents=True, exist_ok=True)

    (src_dir / "live.ts").write_text(read_template("sanity/live.ts"))
    print(f"  Created: {src_dir / 'live.ts'}")


def create_fetch_helper(output_dir: Path) -> None:
    """Create the sanityFetch helper for draft mode."""
    src_dir = output_dir / "frontend" / "src" / "sanity" / "lib"
    src_dir.mkdir(parents=True, exist_ok=True)

    (src_dir / "fetch.ts").write_text(read_template("sanity/fetch.ts"))
    print(f"  Created: {src_dir / 'fetch.ts'}")


def create_draft_mode_routes(output_dir: Path) -> None:
    """Create enable/disable draft mode API routes."""
    api_dir = output_dir / "frontend" / "src" / "app" / "api" / "draft-mode"

    enable_dir = api_dir / "enable"
    enable_dir.mkdir(parents=True, exist_ok=True)
    (enable_dir / "route.ts").write_text(read_template("nextjs/enable-draft.ts"))
    print(f"  Created: {enable_dir / 'route.ts'}")

    disable_dir = api_dir / "disable"
    disable_dir.mkdir(parents=True, exist_ok=True)
    (disable_dir / "route.ts").write_text(read_template("nextjs/disable-draft.ts"))
    print(f"  Created: {disable_dir / 'route.ts'}")


def create_disable_draft_mode_component(output_dir: Path) -> None:
    """Create the Disable Draft Mode button component."""
    components_dir = output_dir / "frontend" / "src" / "components"
    components_dir.mkdir(parents=True, exist_ok=True)

    (components_dir / "DisableDraftMode.tsx").write_text(
        read_template("components/DisableDraftMode.tsx")
    )
    print(f"  Created: {components_dir / 'DisableDraftMode.tsx'}")


def update_layout(output_dir: Path) -> None:
    """Update root layout with Visual Editing components."""
    layout_path = output_dir / "frontend" / "src" / "app" / "layout.tsx"

    if layout_path.exists():
        layout_path.write_text(read_template("nextjs/layout.tsx"))
        print(f"  Updated: {layout_path}")
    else:
        print(f"  Warning: {layout_path} not found, skipping layout update")


def create_sanity_config(output_dir: Path, project_name: str) -> None:
    """Create Sanity config with Presentation tool."""
    studio_dir = output_dir / "studio"

    config_path = studio_dir / "sanity.config.ts"

    config_content = (
        read_template("sanity/sanity.config.ts")
        .replace("__PROJECT_NAME__", project_name.lower().replace(" ", "-"))
        .replace("__PROJECT_TITLE__", project_name)
    )

    config_path.write_text(config_content)
    print(f"  Created: {config_path}")


def install_dependencies(output_dir: Path) -> None:
    """Install required npm packages for Visual Editing."""
    import subprocess

    frontend_dir = output_dir / "frontend"

    print("\nInstalling npm packages...")

    packages = ["next-sanity@latest", "@sanity/client", "@sanity/visual-editing"]

    for pkg in packages:
        try:
            subprocess.run(
                ["npm", "install", pkg],
                cwd=frontend_dir,
                check=True,
            )
            print(f"  Installed: {pkg}")
        except subprocess.CalledProcessError as e:
            print(f"  Warning: Failed to install {pkg}: {e}")


def setup_visual_editing(output_dir: Path, project_name: str) -> None:
    """Main function to set up all Visual Editing components."""
    print("\nSetting up Visual Editing...")

    create_sanity_client(output_dir)
    create_fetch_helper(output_dir)
    create_live_mode(output_dir)
    create_draft_mode_routes(output_dir)
    create_disable_draft_mode_component(output_dir)
    update_layout(output_dir)
    create_sanity_config(output_dir, project_name)

    print("\nVisual Editing setup complete!")
