from __future__ import annotations

import sys
from pathlib import Path
from config import settings


if __package__ is None or __package__ == "":
    # When executed as `python figma_worker/main.py`, ensure repo root is importable
    current_dir = Path(__file__).resolve().parent
    repo_root = current_dir.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from figma_worker.figma_connection import FigmaConnection  # type: ignore
else:
    from .figma_connection import FigmaConnection

def main():
    if not settings.figma_api_key:
        raise ValueError("FIGMA_API_KEY not set in environment")

    figma_project_key = settings.figma_file_key
    
    # Prompt for file key if not set
    if not figma_project_key:
        print("\n⚠️  Figma file key not set for this project")
        print("Find it in your Figma URL: https://www.figma.com/design/FILE_KEY_HERE/...")
        figma_project_key = input("Enter Figma file key: ").strip()
        if not figma_project_key:
            raise ValueError("Figma file key is required")
        
        # Save it to settings
        settings.figma_file_key = figma_project_key
        print(f"✓ Saved Figma file key to project settings")

    settings.update_settings()

    canvas_name = str(input("Enter the Figma Page/Canvas name (leave blank for Delivery): ")).strip()
    start_canvas_name = canvas_name or "Delivery"

    figma_connection = FigmaConnection(
        settings.figma_api_key,
        figma_project_key,
        project_id=settings.id,
        start_canvas_name=start_canvas_name,
        fetch_screenshots=True,
    )

    # figma_connection.get_developer_variables()

    figma_connection.get_file()

    # figma_connection.hydrate_components()

if __name__ == "__main__":
    main()



