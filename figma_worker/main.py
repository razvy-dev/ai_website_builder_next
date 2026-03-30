from __future__ import annotations

import sys
from pathlib import Path


if __package__ is None or __package__ == "":
    # When executed as `python figma_worker/main.py`, ensure repo root is importable
    current_dir = Path(__file__).resolve().parent
    repo_root = current_dir.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from figma_worker.figma_connection import FigmaConnection  # type: ignore
else:
    from .figma_connection import FigmaConnection

from config import settings

def main():
    if not settings.figma_api_key:
        raise ValueError("FIGMA_API_KEY not set in environment")

    figma_project_key = str(input("Enter the Figma Project Key: "))
    figma_project_key = figma_project_key.strip()

    canvas_name = str(input("Enter the Figma Page/Canvas name (leave blank for Delivery): ")).strip()
    start_canvas_name = canvas_name or None

    figma_connection = FigmaConnection(
        settings.figma_api_key,
        figma_project_key,
        start_canvas_name=start_canvas_name,
    )

    # figma_connection.get_developer_variables()

    figma_connection.get_file()

    # figma_connection.hydrate_components()

if __name__ == "__main__":
    main()



