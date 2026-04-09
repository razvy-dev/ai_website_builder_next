# Database Architecture

## Overview

This application uses a **multi-database architecture** to separate project metadata from project-specific data:

1. **Settings Database** (`settings.db`) - Contains the `Project` table with metadata for all projects
2. **Project-Specific Databases** (`{project_id}.db`) - Each project has its own database containing Figma data

## Database Structure

### Settings Database (`settings.db`)

Contains a single table:

- **`projects`** - Metadata for all projects
  - `id` (PRIMARY KEY) - Project identifier
  - `name` (UNIQUE) - Project name
  - `description` - Project description
  - `project_path` (UNIQUE) - Path to project directory
  - `figma_database_name` (UNIQUE, NULLABLE) - Legacy field
  - `figma_file_key` (UNIQUE, NULLABLE) - Figma file key
  - `sanity_project_id` (UNIQUE, NULLABLE) - Sanity project ID
  - `sanity_dataset` - Sanity dataset name (default: "production")
  - `sanity_api_read_token` (NULLABLE) - Sanity API token
  - `started_at` (NULLABLE) - Project creation timestamp
  - `updated_at` (NULLABLE) - Last update timestamp

### Project Database (`{project_id}.db`)

Each project has its own database with the following tables:

- **`component_sets`** - Figma component sets (variant groups)
- **`components`** - Main component definitions
- **`pages`** - Figma pages/canvases
- **`frames`** - Top-level artboards/screens
- **`section_components`** - Nested subframes promoted as components
- **`extracted_images`** - Embedded images from designs
- **`component_usages`** - Junction table tracking component instances
- **`variable_collections`** - Design token collections (Enterprise)
- **`variables`** - Design tokens (Enterprise)

## Usage

### Getting Database Sessions

```python
from db.manager import get_settings_session, get_project_session

# Get settings database session
settings_session = get_settings_session()

# Get project-specific database session
project_session = get_project_session(project_id="my_project")
```

### Using DatabaseManager Directly

```python
from db.manager import DatabaseManager

# Initialize with custom directory
db_manager = DatabaseManager(db_dir="./databases")

# Get sessions
settings_session = db_manager.get_settings_session()
project_session = db_manager.get_project_session("my_project")

# Close all connections when done
db_manager.close_all()
```

## Migration Notes

### Changes from Previous Architecture

1. **Unique Constraints**: Optional fields now use `None` instead of empty strings to avoid UNIQUE constraint violations
2. **Separate Databases**: Project data is now isolated in separate database files
3. **Removed Function**: `create_db_and_tables()` has been replaced with `DatabaseManager`

### Updating Existing Code

**Before:**
```python
from db.state import create_db_and_tables
session = create_db_and_tables("figma.db")
```

**After:**
```python
from db.manager import get_project_session
session = get_project_session(project_id)
```

## Benefits

1. **Isolation**: Each project's data is completely isolated
2. **Scalability**: Easy to backup, restore, or delete individual projects
3. **Performance**: Smaller database files improve query performance
4. **Flexibility**: Projects can be moved or shared independently
5. **Data Integrity**: UNIQUE constraints work correctly with NULL values

## File Locations

By default, all database files are stored in the project root directory:
- `settings.db` - Settings database
- `{project_id}.db` - Project-specific databases (e.g., `my_project.db`)

You can customize the location by passing `db_dir` to `DatabaseManager`.
