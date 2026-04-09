from sqlmodel import SQLModel, Field
from typing import Optional

class Project(SQLModel, table=True):
    __tablename__ = "projects"
    
    id: str = Field(primary_key=True)
    name: str = Field(unique=True)
    description: str = Field(default="")
    project_path: str = Field(unique=True)
    figma_database_name: Optional[str] = Field(default=None, unique=True)
    figma_file_key: Optional[str] = Field(default=None, unique=True)
    sanity_project_id: Optional[str] = Field(default=None, unique=True)
    sanity_dataset: str = Field(default="production")
    sanity_api_read_token: Optional[str] = Field(default=None)
    started_at: Optional[str] = Field(default=None)
    updated_at: Optional[str] = Field(default=None)

    