import subprocess
from pathlib import Path


NEXTJS_ENV_TEMPLATE = """# Next.js - Public (exposed to browser)
NEXT_PUBLIC_SANITY_PROJECT_ID={project_id}
NEXT_PUBLIC_SANITY_DATASET=production
NEXT_PUBLIC_SANITY_API_VERSION=2024-12-01
NEXT_PUBLIC_SANITY_STUDIO_URL={studio_url}

# Next.js - Private (server-side only)
# Get this from Sanity Manage (sanity manage) or create a token with Viewer permission
SANITY_VIEWER_TOKEN={viewer_token}
"""

SANITY_ENV_TEMPLATE = """# Sanity Studio - Private (used by Studio)
SANITY_PROJECT_ID={project_id}
SANITY_DATASET=production

# Preview origin - your Next.js frontend URL
SANITY_STUDIO_PREVIEW_ORIGIN={preview_origin}
"""


def get_sanity_projects() -> list[dict]:
    """Get list of Sanity projects from CLI."""
    try:
        result = subprocess.run(
            ["npx", "sanity@latest", "projects", "list", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        import json

        projects = json.loads(result.stdout)
        return projects if isinstance(projects, list) else []
    except Exception as e:
        print(f"Could not fetch Sanity projects: {e}")
        return []


def prompt_for_project_id() -> tuple[str, str]:
    """Prompt user for Sanity project ID and related info."""
    projects = get_sanity_projects()

    if projects:
        print("\nAvailable Sanity projects:")
        for i, p in enumerate(projects, 1):
            print(f"  {i}. {p.get('name', 'Unnamed')} ({p.get('projectId', 'N/A')})")
        print("  0. Enter manually")

        choice = input("\nSelect a project (number): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(projects):
            selected = projects[int(choice) - 1]
            project_id = selected.get("projectId", "")
            studio_url = f"https://{project_id}.sanity.studio"
            return project_id, studio_url

    print("\nEnter project details manually:")
    project_id = input("  Sanity Project ID: ").strip()
    studio_url = (
        f"https://{project_id}.sanity.studio"
        if project_id
        else "https://your-studio.sanity.studio"
    )

    return project_id, studio_url


def generate_nextjs_env(
    output_dir: Path,
    project_id: str,
    studio_url: str,
    viewer_token: str = "YOUR_VIEWER_TOKEN_HERE",
) -> None:
    """Generate .env.local for Next.js frontend."""
    env_content = NEXTJS_ENV_TEMPLATE.format(
        project_id=project_id,
        studio_url=studio_url,
        viewer_token=viewer_token,
    )

    env_path = output_dir / "frontend" / ".env.local"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(env_content)
    print(f"  Created: {env_path}")


def generate_sanity_env(
    output_dir: Path, project_id: str, preview_origin: str = "http://localhost:3000"
) -> None:
    """Generate .env for Sanity Studio."""
    env_content = SANITY_ENV_TEMPLATE.format(
        project_id=project_id,
        preview_origin=preview_origin,
    )

    env_path = output_dir / "studio" / ".env"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(env_content)
    print(f"  Created: {env_path}")


def write_env_files(output_dir: Path, project_id: str | None = None) -> None:
    """Main function to generate all .env files."""
    if not project_id:
        project_id, studio_url = prompt_for_project_id()
    else:
        studio_url = f"https://{project_id}.sanity.studio"

    if not project_id:
        print("Error: No project ID provided. Skipping .env generation.")
        return

    print("\nGenerating .env files...")

    generate_nextjs_env(output_dir, project_id, studio_url)
    generate_sanity_env(output_dir, project_id)

    print("\n.env files generated successfully!")
    print("Note: Update SANITY_VIEWER_TOKEN with a token from sanity manage")
