from pathlib import Path
from .runner import run
from .env_writer import write_env_files, get_sanity_projects
from .scaffold import setup_visual_editing


def prompt_for_sanity_project() -> str | None:
    """Prompt user to select or create a Sanity project."""
    projects = get_sanity_projects()

    if projects:
        print("\nAvailable Sanity projects:")
        for i, p in enumerate(projects, 1):
            print(f"  {i}. {p.get('name', 'Unnamed')} ({p.get('projectId', 'N/A')})")
        print("  N. Create a new project (will open browser)")
        print("  S. Skip Sanity Studio setup")

        choice = input("\nSelect a project (number, N, or S): ").strip().upper()

        if choice == "S" or choice == "SKIP":
            return None
        elif choice == "N" or choice == "NEW":
            print("\nTo create a new project:")
            print("1. Go to https://www.sanity.io/manage")
            print("2. Create a new project")
            print("3. Run this script again and select your new project")
            return None
        elif choice.isdigit() and 1 <= int(choice) <= len(projects):
            return projects[int(choice) - 1].get("projectId", "")

    return None


def main():
    project_name = str(input("Enter this project's name: "))

    BUILDER_ROOT = Path(__file__).resolve().parent.parent
    OUTPUT_DIR = BUILDER_ROOT / project_name

    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"\nCreating Next.js frontend in: {OUTPUT_DIR}")
    run(
        [
            "npx",
            "create-next-app@latest",
            "frontend",
            "--ts",
            "--tailwind",
            "--app",
            "--src-dir",
            "--yes",
        ],
        cwd=OUTPUT_DIR,
    )

    # Get Sanity project ID
    project_id = prompt_for_sanity_project()

    if project_id:
        print(f"\nCreating Sanity Studio with project: {project_id}")
        run(
            [
                "npx",
                "sanity@latest",
                "init",
                "-y",
                "--project-id",
                project_id,
                "--dataset",
                "production",
                "--output-path",
                str(OUTPUT_DIR / "studio"),
            ],
            cwd=OUTPUT_DIR,
        )

        # Generate env files with the project ID
        write_env_files(OUTPUT_DIR, project_id=project_id)
    else:
        print("\nSkipping Sanity Studio setup.")
        print("To set up manually:")
        print("1. Go to https://www.sanity.io/manage")
        print("2. Create a new project")
        print("3. Run: cd studio && sanity init")

        # Still generate env files template
        write_env_files(OUTPUT_DIR, project_id="YOUR_PROJECT_ID")

    setup_visual_editing(OUTPUT_DIR, project_name)

    print(f"\n--- Project Setup Complete! ---\n")
    print(f"Project: {project_name}")
    print(f"Location: {OUTPUT_DIR}")
    print(f"  - Frontend: {OUTPUT_DIR / 'frontend'}")
    print(f"  - Studio:   {OUTPUT_DIR / 'studio'}")

    print("\n=== ALL DONE ===")
    print("\nNext steps:")
    print("1. Update SANITY_VIEWER_TOKEN in frontend/.env.local")
    print("   Run: npx sanity manage")
    print("   Create a token with Viewer permission")
    print("2. Start frontend: cd frontend && npm run dev")
    print("3. Start studio:   cd studio  && npm run dev")


if __name__ == "__main__":
    main()
