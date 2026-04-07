from sqlmodel import SQLModel, Field, create_engine, Session
from typing import Optional

class Project(SQLModel, table=True):
    __tablename__ = "projects"
    
    id: str = Field(primary_key=True)
    name: str = Field(unique=True)
    description: str = Field(default="")
    project_path: str = Field(unique=True)
    figma_database_name: str = Field(unique=True)
    figma_file_key: str = Field(unique=True)
    sanity_project_id: str = Field(unique=True)
    sanity_dataset: str = Field(default="production")
    sanity_api_read_token: str = Field(default="")
    started_at: Optional[str] = Field(default=None)
    updated_at: Optional[str] = Field(default=None)

def create_db_and_tables(db_path: str = "settings.db") -> Session:
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)

    