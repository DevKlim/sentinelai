import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional

class Settings(BaseSettings):
    """
    Pydantic settings class to manage environment variables for the EIDO agent.
    Values are automatically read from environment variables or a .env file.
    """
    # This was added to fix a previous AttributeError
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # API settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")

    # Database connection URL
    # This is critical and must be set in the environment.
    database_url: str = Field(..., env="DATABASE_URL")

    @field_validator('database_url')
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        """
        Validates and corrects the database URL for SQLAlchemy async compatibility.
        - Ensures the 'postgresql+asyncpg' driver is used.
        - Strips all query parameters (like ?sslmode) so they can be handled
          explicitly by the engine's connect_args.
        """
        if not v:
            return v
        
        # Split the URL at the first '?' to remove all query parameters.
        base_url = v.split("?")[0]

        if base_url.startswith("postgres://"):
            return base_url.replace("postgres://", "postgresql+asyncpg://", 1)
        
        if base_url.startswith("postgresql://") and "+asyncpg" not in base_url:
            return base_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        return base_url

    # LLM Provider settings
    llm_provider: str = Field(default="google", env="LLM_PROVIDER")
    
    # Google Gemini settings
    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    google_model_name: str = Field(default="gemini-2.5-flash-lite", env="GOOGLE_MODEL_NAME")

    # OpenAI settings (optional)
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model_name: str = Field(default="gpt-5", env="OPENAI_MODEL_NAME")

    # Local LLM settings (optional)
    local_llm_url: Optional[str] = Field(default=None, env="LOCAL_LLM_URL")

    # Geocoding service settings
    geocoding_user_agent: str = Field(default="sdsc-orchestrator-project", env="GEOCODING_USER_AGENT")

    # Embedding model settings
    embedding_model_name: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL_NAME")

    # Incident matching settings
    time_window_minutes: int = Field(default=60, env="TIME_WINDOW_MINUTES")
    distance_threshold_km: float = Field(default=1.0, env="DISTANCE_THRESHOLD_KM")
    similarity_threshold: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    content_similarity_min_common_words: int = Field(default=2, env="CONTENT_SIMILARITY_MIN_COMMON_WORDS")

    # Configuration for Pydantic BaseSettings
    model_config = SettingsConfigDict(
        # In case a .env file is used within the eido-agent directory
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore' # Ignore extra fields from environment
    )

# Instantiate the settings object to be imported by other modules
settings = Settings()