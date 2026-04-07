from pathlib import Path
import os
import subprocess
import sys
from config import settings

# Add parent directory to path for imports
if __package__ is None or __package__ == "":
    current_dir = Path(__file__).resolve().parent
    repo_root = current_dir.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from .runner import run, run_capture


def is_sanity_authenticated() -> bool:
    """Best-effort signal for whether the user is logged into the Sanity CLI."""
    if os.getenv("SANITY_AUTH_TOKEN"):
        return True

    sanity_rc = Path.home() / ".sanityrc"
    if sanity_rc.exists():
        try:
            content = sanity_rc.read_text()
        except Exception:
            return True

        if "authToken" in content or "cliToken" in content or content.strip():
            return True

    return False


def check_sanity_cli() -> bool:
    """Check if user is logged into Sanity CLI."""
    if not is_sanity_authenticated():
        print("\n⚠️  You need to be logged into Sanity CLI to use this template.")
        print("\nPlease run one of the following:")
        print("  npx sanity login")
        print("  or set SANITY_AUTH_TOKEN environment variable")
        
        choice = input("\nWould you like to login now? (y/n): ").strip().lower()
        if choice == 'y':
            try:
                run(["npx", "sanity@latest", "login"], cwd=".")
                return True
            except Exception as e:
                print(f"\n✗ Login failed: {e}")
                return False
        return False
    return True


def get_project_config(project_dir: Path) -> dict | None:
    """Extract Sanity project configuration from the created project."""
    # Try to find sanity.cli.ts or sanity.config.ts
    config_files = [
        project_dir / "sanity.cli.ts",
        project_dir / "sanity.config.ts",
        project_dir / "studio" / "sanity.cli.ts",
        project_dir / "studio" / "sanity.config.ts",
    ]
    
    for config_file in config_files:
        if config_file.exists():
            try:
                content = config_file.read_text()
                # Extract projectId from config
                import re
                project_match = re.search(r"projectId:\s*['\"]([^'\"]+)['\"]|SANITY_PROJECT_ID\s*:\s*['\"]([^'\"]+)['\"]", content)
                dataset_match = re.search(r"dataset:\s*['\"]([^'\"]+)['\"]|SANITY_DATASET\s*:\s*['\"]([^'\"]+)['\"]", content)
                
                if project_match:
                    project_id = project_match.group(1) or project_match.group(2)
                    dataset = dataset_match.group(1) or dataset_match.group(2) if dataset_match else "production"
                    return {"projectId": project_id, "dataset": dataset}
            except Exception:
                pass
    
    # Try .env files
    env_files = [
        project_dir / ".env",
        project_dir / ".env.local",
        project_dir / "studio" / ".env",
    ]
    
    for env_file in env_files:
        if env_file.exists():
            try:
                content = env_file.read_text()
                lines = content.split("\n")
                config = {}
                for line in lines:
                    if "PROJECT_ID" in line and "=" in line:
                        config["projectId"] = line.split("=", 1)[1].strip().strip('"\'')
                    if "DATASET" in line and "=" in line:
                        config["dataset"] = line.split("=", 1)[1].strip().strip('"\'')
                if config.get("projectId"):
                    return config
            except Exception:
                pass
    
    return None


def init_project():
    """Main function following official Sanity Next.js Clean template guide."""
    print("\n" + "="*60)
    print("   Sanity Next.js Clean Template Setup")
    print("   Following: https://www.sanity.io/templates/nextjs-sanity-clean")
    print("="*60)
    
    # Check authentication first
    if not check_sanity_cli():
        print("\n✗ Setup cancelled. Please authenticate with Sanity CLI first.")
        return
    
    project_name = input("\nEnter your project name: ").strip()
    description = input("Enter project description: ").strip()
    if not project_name:
        project_name = "my-sanity-app"
        print(f"Using default name: {project_name}")
    
    # Use parent directory to avoid npm detecting Python framework
    PYTHON_PROJECT_ROOT = Path(__file__).resolve().parent.parent
    BUILDER_ROOT = PYTHON_PROJECT_ROOT.parent
    OUTPUT_DIR = BUILDER_ROOT / project_name
    
    # Check if directory exists
    if OUTPUT_DIR.exists():
        print(f"\n⚠️  Directory '{OUTPUT_DIR}' already exists.")
        overwrite = input("Continue anyway? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("Setup cancelled.")
            return
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    print(f"\n📦 Installing Sanity Next.js Clean template...")
    print(f"   Location: {OUTPUT_DIR}")
    print("\n   This will:")
    print("   • Create a Next.js 16 app with App Router")
    print("   • Set up Sanity Studio with Visual Editing")
    print("   • Configure Live Content API")
    print("   • Add Presentation Tool for real-time editing")
    print("")
    
    # Run the official template installation command
    cmd = [
        "npm",
        "create",
        "sanity@latest",
        "--",
        "--template",
        "sanity-io/sanity-template-nextjs-clean",
        "--output-path",
        project_name,
        "--no-mcp",
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print("\n" + "-"*60)
    
    try:
        run(cmd, cwd=BUILDER_ROOT)
        print("\n" + "-"*60)
        print("\n✓ Template installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Template installation failed (exit code {e.returncode})")
        print("\nYou can try installing manually:")
        print(f"  cd {BUILDER_ROOT}")
        print(f"  npm create sanity@latest -- --template sanity-io/sanity-template-nextjs-clean")
        return
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return
    
    # Extract project configuration
    config = get_project_config(OUTPUT_DIR)
    
    # Save to global state for use by other parts of the system
    if config:
        try:
            from ai_worker.utils.global_state import set_project_config
            
            # Get token from environment or prompt user
            sanity_token = os.getenv("SANITY_AUTH_TOKEN")
            if not sanity_token:
                print("\n⚠️  SANITY_AUTH_TOKEN not found in environment.")
                print("You can set it later in the .env file or provide it now.")
                token_input = input("Enter Sanity auth token (or press Enter to skip): ").strip()
                sanity_token = token_input if token_input else None
            
            set_project_config(
                project_name=project_name,
                project_path=str(OUTPUT_DIR),
                sanity_project_id=config.get('projectId', ''),
                sanity_dataset=config.get('dataset', 'production'),
                sanity_token=sanity_token
            )
        except Exception as e:
            print(f"\n⚠️  Could not save project configuration: {e}")
    
    print("\n" + "="*60)
    print("   Setup Complete!")
    print("="*60)
    print(f"\n📁 Project: {project_name}")
    print(f"   Location: {OUTPUT_DIR}")
    
    if config:
        print(f"\n🔧 Configuration:")
        print(f"   Project ID: {config.get('projectId', 'N/A')}")
        print(f"   Dataset: {config.get('dataset', 'production')}")
        print(f"   Studio URL: https://{config.get('projectId', 'your-project')}.sanity.studio")
    
    print("\n📚 What's included:")
    print("   ✓ Next.js 16 with App Router")
    print("   ✓ Sanity Studio with Visual Editing")
    print("   ✓ Live Content API integration")
    print("   ✓ Presentation Tool for real-time preview")
    print("   ✓ Pre-configured schema (Page, Post, Person, Settings)")
    print("   ✓ Drag-and-drop page builder")
    
    print("\n🚀 Next Steps:")
    print(f"\n1. Navigate to your project:")
    print(f"   cd {OUTPUT_DIR}")
    
    print("\n2. Start the development servers:")
    print("   npm run dev")
    
    print("\n3. Open in your browser:")
    print("   • Next.js app: http://localhost:3000")
    print("   • Sanity Studio: http://localhost:3333")
    
    print("\n4. (Optional) Import sample data:")
    print("   npm run import-sample-data")
    
    print("\n5. Deploy when ready:")
    print("   • Studio: npx sanity deploy")
    print("   • Next.js: Deploy to Vercel or your preferred host")
    
    print("\n📖 Documentation:")
    print("   • Template: https://www.sanity.io/templates/nextjs-sanity-clean")
    print("   • Sanity Docs: https://www.sanity.io/docs")
    print("   • Visual Editing: https://www.sanity.io/docs/presentation")
    
    print("\n" + "="*60)

    settings.id = project_name
    settings.name = project_name
    settings.description = description
    settings.project_path = str(OUTPUT_DIR)
    settings.figma_database_name = ""
    settings.figma_file_key = ""
    settings.sanity_project_id = config.get('projectId', '')
    settings.sanity_dataset = config.get('dataset', 'production')
    settings.sanity_api_read_token = ""
    settings.started_at = ""
    settings.updated_at = ""


if __name__ == "__main__":
    main()
