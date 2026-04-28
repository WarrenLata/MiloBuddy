from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "milo-backend"
    # Avoid clashing with generic DEBUG env vars (e.g. "release") coming from the host.
    debug: bool = Field(default=True, validation_alias="MILO_DEBUG")
    # Google Cloud project id to use with ADK / Vertex AI
    gcloud_project_id: str = "project-83496149-f0b4-4517-b42"
    GOOGLE_CLOUD_PROJECT: str = "project-83496149-f0b4-4517-b42"
    # Default ADK model to use for the main agent
    adk_model: str = "gemini-3-flash-preview"
    # Server host/port for local uvicorn run (can be overridden via .env)
    host: str = "127.0.0.1"
    port: int = 8000
    # Whether to enable uvicorn reload (useful in development)
    reload: bool = True
    google_api_key: str = ""

    # Pydantic v2: load environment variables from a .env file by default
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
