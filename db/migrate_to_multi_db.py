#!/usr/bin/env python3
"""
Migration script to convert from single database to multi-database architecture.

This script:
1. Reads the old settings.db (if it exists)
2. Creates the new settings.db with updated schema
3. For each project, creates a separate {project_id}.db file
4. Migrates Figma data from old figma.db to project-specific databases

Usage:
    python db/migrate_to_multi_db.py
"""

import sqlite3
import shutil
from pathlib import Path
from datetime import datetime


def backup_databases():
    """Create backups of existing databases."""
    backup_dir = Path("db_backups") / datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_backup = ["settings.db", "figma.db"]
    backed_up = []
    
    for db_file in files_to_backup:
        if Path(db_file).exists():
            backup_path = backup_dir / db_file
            shutil.copy2(db_file, backup_path)
            backed_up.append(db_file)
            print(f"✓ Backed up {db_file} to {backup_path}")
    
    return backup_dir if backed_up else None


def migrate_settings_db():
    """Migrate settings database to new schema with NULL support."""
    old_db = Path("settings.db")
    
    if not old_db.exists():
        print("No existing settings.db found. Creating new one...")
        from db.manager import get_settings_session
        session = get_settings_session()
        session.close()
        return []
    
    print("\n=== Migrating settings.db ===")
    
    # Read existing projects
    conn = sqlite3.connect(old_db)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM projects")
        columns = [description[0] for description in cursor.description]
        projects = []
        
        for row in cursor.fetchall():
            project = dict(zip(columns, row))
            # Convert empty strings to None for optional fields
            for field in ['figma_database_name', 'figma_file_key', 'sanity_project_id', 
                         'sanity_api_read_token', 'started_at', 'updated_at']:
                if field in project and project[field] == '':
                    project[field] = None
            projects.append(project)
        
        print(f"Found {len(projects)} projects to migrate")
        
    except sqlite3.OperationalError as e:
        print(f"Error reading old database: {e}")
        projects = []
    finally:
        conn.close()
    
    # Rename old database
    old_db.rename("settings.db.old")
    
    # Create new database with updated schema
    from db.manager import get_settings_session
    from db.state import Project
    
    session = get_settings_session()
    
    # Insert projects with new schema
    for project_data in projects:
        try:
            project = Project(**project_data)
            session.add(project)
            session.commit()
            print(f"✓ Migrated project: {project.name}")
        except Exception as e:
            print(f"✗ Error migrating project {project_data.get('name')}: {e}")
            session.rollback()
    
    session.close()
    return projects


def migrate_figma_data(projects):
    """Migrate Figma data to project-specific databases."""
    old_figma_db = Path("figma.db")
    
    if not old_figma_db.exists():
        print("\nNo figma.db found. Skipping Figma data migration.")
        return
    
    print("\n=== Migrating Figma data ===")
    
    # If there's only one project, migrate all data to that project's database
    if len(projects) == 1:
        project_id = projects[0]['id']
        new_db = Path(f"{project_id}.db")
        
        print(f"Copying figma.db to {new_db}...")
        shutil.copy2(old_figma_db, new_db)
        print(f"✓ Migrated Figma data to {new_db}")
        
        # Rename old database
        old_figma_db.rename("figma.db.old")
    else:
        print("⚠️  Multiple projects found. Cannot automatically migrate figma.db")
        print("   Please manually assign Figma data to the correct project databases.")
        print("   You can copy figma.db to {project_id}.db for each project.")


def main():
    """Run the migration."""
    print("="*60)
    print("Database Migration: Single DB → Multi-Database Architecture")
    print("="*60)
    
    # Create backups
    backup_dir = backup_databases()
    if backup_dir:
        print(f"\n✓ Backups created in: {backup_dir}")
    
    # Migrate settings
    projects = migrate_settings_db()
    
    # Migrate Figma data
    if projects:
        migrate_figma_data(projects)
    
    print("\n" + "="*60)
    print("Migration complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Test your application with the new database structure")
    print("2. If everything works, you can delete the .old backup files")
    print("3. Check db/README.md for the new database architecture documentation")


if __name__ == "__main__":
    main()
