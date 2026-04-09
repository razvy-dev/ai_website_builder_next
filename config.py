from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from db.state import Project
from sqlmodel import select

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    figma_api_key: Optional[str] = None

    # Project settings
    id: str = ""
    name: str = ""
    description: str = ""
    project_path: str = ""
    figma_database_name: Optional[str] = None
    figma_file_key: Optional[str] = None
    sanity_project_id: Optional[str] = None
    sanity_dataset: str = "production"
    sanity_api_read_token: Optional[str] = None
    started_at: Optional[str] = None
    updated_at: Optional[str] = None

    dev: bool = False

    def update_settings(self):
        """Update or create project settings in the settings database."""
        from db.manager import get_settings_session
        
        session = get_settings_session()
        
        try:
            statement = select(Project).where(Project.id == self.id)
            project = session.exec(statement).first()
            
            if project:
                # Update existing project
                project.name = self.name
                project.description = self.description
                project.project_path = self.project_path
                project.figma_database_name = self.figma_database_name or None
                project.figma_file_key = self.figma_file_key or None
                project.sanity_project_id = self.sanity_project_id or None
                project.sanity_dataset = self.sanity_dataset
                project.sanity_api_read_token = self.sanity_api_read_token or None
                project.started_at = self.started_at
                project.updated_at = self.updated_at
                session.add(project)
                session.commit()
                session.refresh(project)
            else:
                # Create new project
                project = Project(
                    id=self.id,
                    name=self.name,
                    description=self.description,
                    project_path=self.project_path,
                    figma_database_name=self.figma_database_name or None,
                    figma_file_key=self.figma_file_key or None,
                    sanity_project_id=self.sanity_project_id or None,
                    sanity_dataset=self.sanity_dataset,
                    sanity_api_read_token=self.sanity_api_read_token or None,
                    started_at=self.started_at,
                    updated_at=self.updated_at,
                )
                session.add(project)
                session.commit()
                session.refresh(project)
        finally:
            session.close()


settings = Settings()
