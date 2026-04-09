"""
Database Manager - Handles settings database and project-specific databases.

Architecture:
- settings.db: Contains the Project table (metadata for all projects)
- {project_id}.db: Each project has its own database with Figma data tables
"""
from sqlmodel import Session, create_engine, SQLModel
from typing import Optional
from pathlib import Path


class DatabaseManager:
    """Manages multiple databases: one settings DB and multiple project DBs."""
    
    SETTINGS_DB = "settings.db"
    
    def __init__(self, db_dir: str = "."):
        """
        Initialize the database manager.
        
        Args:
            db_dir: Directory where database files are stored
        """
        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(exist_ok=True)
        self._engines = {}
    
    def get_settings_session(self) -> Session:
        """
        Get a session for the settings database.
        
        Returns:
            SQLModel Session connected to settings.db
        """
        db_path = self.db_dir / self.SETTINGS_DB
        
        if self.SETTINGS_DB not in self._engines:
            from sqlalchemy import MetaData
            from db.state import Project
            
            engine = create_engine(
                f"sqlite:///{db_path}",
                connect_args={"check_same_thread": False},
            )
            
            # Create isolated metadata containing ONLY the Project table
            # This prevents all other SQLModel tables from being created here
            isolated_metadata = MetaData()
            
            # Copy only the Project table definition to isolated metadata
            # This ensures we don't pull in any tables from db.migration
            Project.__table__.to_metadata(isolated_metadata)
            
            # Create only the projects table
            isolated_metadata.create_all(engine)
            
            self._engines[self.SETTINGS_DB] = engine
        
        return Session(self._engines[self.SETTINGS_DB])
    
    def get_project_session(self, project_id: str) -> Session:
        """
        Get a session for a specific project's database.
        
        Args:
            project_id: The project identifier (used as database filename)
            
        Returns:
            SQLModel Session connected to {project_id}.db
        """
        db_name = f"{project_id}.db"
        db_path = self.db_dir / db_name
        
        if db_name not in self._engines:
            from sqlalchemy import MetaData, Table, Column, String, Integer, Float, Boolean, ForeignKey
            
            engine = create_engine(
                f"sqlite:///{db_path}",
                connect_args={"check_same_thread": False},
            )
            
            # Create isolated metadata - manually define tables to avoid global metadata
            isolated_metadata = MetaData()
            
            # Define all project-specific tables manually
            Table('component_sets', isolated_metadata,
                Column('key', String, primary_key=True),
                Column('node_id', String, unique=True),
                Column('name', String),
                Column('description', String, default=''),
            )
            
            Table('components', isolated_metadata,
                Column('key', String, primary_key=True),
                Column('node_id', String, unique=True),
                Column('name', String),
                Column('description', String, default=''),
                Column('remote', Boolean, default=False),
                Column('raw_node_json', String, nullable=True),
                Column('screenshot', String, nullable=True),
                Column('updated_at', String, nullable=True),
                Column('width', Float, nullable=True),
                Column('height', Float, nullable=True),
                Column('component_set_key', String, ForeignKey('component_sets.key'), nullable=True),
            )
            
            Table('pages', isolated_metadata,
                Column('page_id', String, primary_key=True),
                Column('page_name', String),
                Column('order', Integer, default=0),
            )
            
            Table('frames', isolated_metadata,
                Column('frame_id', String, primary_key=True),
                Column('frame_name', String),
                Column('width', Float, nullable=True),
                Column('height', Float, nullable=True),
                Column('page_id', String, ForeignKey('pages.page_id')),
            )
            
            Table('section_components', isolated_metadata,
                Column('node_id', String, primary_key=True),
                Column('page_id', String, ForeignKey('pages.page_id')),
                Column('root_frame_id', String, ForeignKey('frames.frame_id')),
                Column('parent_node_id', String, ForeignKey('section_components.node_id'), nullable=True),
                Column('depth', Integer, default=0),
                Column('order', Integer, default=0),
                Column('name', String, default=''),
                Column('width', Float, nullable=True),
                Column('height', Float, nullable=True),
                Column('raw_node_json', String, default='{}'),
                Column('screenshot', String, nullable=True),
            )
            
            Table('extracted_images', isolated_metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('image_ref', String, index=True),
                Column('section_node_id', String, ForeignKey('section_components.node_id')),
                Column('node_id', String),
                Column('node_name', String, default=''),
                Column('node_path', String, default=''),
                Column('local_path', String, nullable=True),
                Column('scale_mode', String, default='FILL'),
            )
            
            Table('component_usages', isolated_metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('instance_node_id', String, unique=True),
                Column('component_key', String, ForeignKey('components.key')),
                Column('page_id', String, ForeignKey('pages.page_id')),
                Column('frame_id', String, ForeignKey('frames.frame_id'), nullable=True),
            )
            
            Table('variable_collections', isolated_metadata,
                Column('collection_id', String, primary_key=True),
                Column('name', String),
                Column('default_mode_id', String),
                Column('modes_json', String, default='[]'),
                Column('remote', Boolean, default=False),
            )
            
            Table('variables', isolated_metadata,
                Column('variable_id', String, primary_key=True),
                Column('name', String),
                Column('resolved_type', String),
                Column('values_by_mode_json', String, default='{}'),
                Column('scopes_json', String, default='[]'),
                Column('code_syntax_json', String, default='{}'),
                Column('remote', Boolean, default=False),
                Column('collection_id', String, ForeignKey('variable_collections.collection_id')),
            )
            
            # Create only project-specific tables
            isolated_metadata.create_all(engine)
            
            self._engines[db_name] = engine
        
        return Session(self._engines[db_name])
    
    def close_all(self):
        """Close all database connections."""
        for engine in self._engines.values():
            engine.dispose()
        self._engines.clear()


# Global instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(db_dir: str = None) -> DatabaseManager:
    """
    Get the global DatabaseManager instance.
    
    Args:
        db_dir: Directory where database files are stored
        
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        if db_dir is None:
            project_root = Path(__file__).parent.parent
            db_dir = str(project_root)
        _db_manager = DatabaseManager(db_dir)
    return _db_manager


def get_settings_session() -> Session:
    """Convenience function to get settings database session."""
    return get_db_manager().get_settings_session()


def get_project_session(project_id: str) -> Session:
    """Convenience function to get project database session."""
    return get_db_manager().get_project_session(project_id)
