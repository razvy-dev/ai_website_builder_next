#!/usr/bin/env python3
"""AI Website Builder - Main Entry Point"""

from project_init.main import main as init_project


def main():
    print("=" * 50)
    print("AI Website Builder")
    print("=" * 50)
    print("\nSelect functionality:")
    print("1. Initialize new project (Next.js + Sanity + Visual Editing)")
    print("2. Figma integration (coming soon)")
    print("3. AI component generation (coming soon)")
    print("4. Assembly (coming soon)")
    print("\n")

    choice = input("Enter your choice (1-4): ").strip()

    if choice == "1":
        init_project()
    elif choice == "2":
        print("Figma integration not yet implemented.")
    elif choice == "3":
        print("AI component generation not yet implemented.")
    elif choice == "4":
        print("Assembly not yet implemented.")
    else:
        print("Invalid choice.")


if __name__ == "__main__":
    main()
