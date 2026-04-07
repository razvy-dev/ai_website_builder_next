#!/usr/bin/env python3
"""AI Website Builder - Main Entry Point"""

from project_init.main import main as init_project
from figma_worker.main import main as figma_integration
from ai_worker.main import main as ai_component_generation
from db.state import Project
from sqlmodel import select
from config import settings

def ask_what_to_do():
    print("=" * 50)
    print("AI Website Builder")
    print("=" * 50)
    print("\nSelect functionality:")
    print("1. Figma integration (we will need you to pass in a file key)")
    print("2. AI component generation (Sanity schemas)")
    print("\n")

    choice = int(input("What would you like to do? "))

    if choice == 1:
        figma_integration()
    elif choice == 2:
        ai_component_generation()
    else:
        print("Invalid choice.")

def main():

    # Create database and tables
    from db.state import create_db_and_tables
    create_db_and_tables()

    # create the settings object to pass to the workers

    # get all projects

    statement = select(Project).order_by(
        Project.started_at
    )
    projects = session.exec(statement).all()

    projects.append("Start a new Project")

    print("What project do you want to work on?")

    for i, project in enumerate(projects):
        print(f"{i + 1}. {project.name}")

    what_project = input(f"Enter your choice (1-{len(projects)}): ").strip()

    if int(what_project) < 0 or int(what_project) > len(projects):
        print("Invalid choice.")
        return

    selected_project = projects[int(what_project) - 1]

    if int(what_project) == len(projects) - 1:
        print("Starting a new project...")
        init_project()
        ask_what_to_do()
        return
    else: 
        settings.id = selected_project.id
        settings.name = selected_project.name
        settings.description = selected_project.description
        settings.project_path = selected_project.project_path
        settings.figma_database_name = selected_project.figma_database_name
        settings.figma_file_key = selected_project.figma_file_key
        settings.sanity_project_id = selected_project.sanity_project_id
        settings.sanity_dataset = selected_project.sanity_dataset
        settings.sanity_api_read_token = selected_project.sanity_api_read_token
        settings.started_at = selected_project.started_at
        settings.updated_at = selected_project.updated_at
        ask_what_to_do()

if __name__ == "__main__":
    main()
