#!/usr/bin/env python3
"""AI Website Builder - Main Entry Point"""

from project_init.main import main as init_project
from figma_worker.main import main as figma_integration
from ai_worker.main import main as ai_component_generation


def main():
    print("=" * 50)
    print("AI Website Builder")
    print("=" * 50)
    print("\nSelect functionality:")
    print("1. Initialize new project (Next.js + Sanity + Visual Editing)")
    print("2. Figma integration (we will need you to pass in a file key)")
    print("3. AI component generation (Sanity schemas)")
    print("4. Assembly (coming soon)")
    print("\n")

    choice = input("Enter your choice (1-4): ").strip()

    if choice == "1":
        init_project()
    elif choice == "2":
        figma_integration()
    elif choice == "3":
        ai_component_generation()
    elif choice == "4":
        print("Assembly not yet implemented.")
    else:
        print("Invalid choice.")


if __name__ == "__main__":
    main()
