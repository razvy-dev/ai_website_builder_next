from pathlib import Path
from runner import run
from env_writer import write_env_files
from scaffold import setup_visual_editing


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

    print(f"\nCreating Sanity Studio in: {OUTPUT_DIR / 'studio'}")
    run(
        [
            "npx",
            "sanity@latest",
            "init",
            "-y",
            "--create-project",
            "sanity",
            "--dataset",
            "production",
            "--output-path",
            str(OUTPUT_DIR / "studio"),
        ],
        cwd=OUTPUT_DIR,
    )

    print(f"\n--- Project Setup Complete! ---\n")
    print(f"Project: {project_name}")
    print(f"Location: {OUTPUT_DIR}")
    print(f"  - Frontend: {OUTPUT_DIR / 'frontend'}")
    print(f"  - Studio:   {OUTPUT_DIR / 'studio'}")

    write_env_files(OUTPUT_DIR)

    setup_visual_editing(OUTPUT_DIR, project_name)

    print("\n=== ALL DONE ===")
    print("\nNext steps:")
    print("1. Update SANITY_VIEWER_TOKEN in frontend/.env.local")
    print("   Run: npx sanity manage")
    print("   Create a token with Viewer permission")
    print("2. Start frontend: cd frontend && npm run dev")
    print("3. Start studio:   cd studio  && npm run dev")


if __name__ == "__main__":
    main()
