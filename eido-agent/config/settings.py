import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional

class Settings(BaseSettings):
    """
    Pydantic settings class to manage environment variables for the EIDO agent.
    Values are automatically read from environment variables or a .env file.
    """
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # API settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")

    # Database connection URL - Made optional to allow build-time scripts to run
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")

    @field_validator('database_url')
    @classmethod
    def fix_database_url(cls, v: Optional[str]) -> Optional[str]:
        """Corrects database URL for SQLAlchemy asyncpg compatibility."""
        if not v:
            return v
        base_url = v.split("?")[0]
        if base_url.startswith("postgres://"):
            return base_url.replace("postgres://", "postgresql+asyncpg://", 1)
        if base_url.startswith("postgresql://") and "+asyncpg" not in base_url:
            return base_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return base_url

    # LLM Provider settings with EIDO_ prefix
    llm_provider: str = Field(default="google", env="EIDO_LLM_PROVIDER")
    
    google_api_key: Optional[str] = Field(default=None, env="EIDO_GOOGLE_API_KEY")
    google_model_name: str = Field(default="gemini-2.5-flash-lite", env="EIDO_GOOGLE_MODEL_NAME")

    openai_api_key: Optional[str] = Field(default=None, env="EIDO_OPENAI_API_KEY")
    openai_model_name: str = Field(default="gpt-5", env="EIDO_OPENAI_MODEL_NAME")
    
    openrouter_api_key: Optional[str] = Field(default=None, env="EIDO_OPENROUTER_API_KEY")

    local_llm_url: Optional[str] = Field(default=None, env="EIDO_LOCAL_LLM_URL")

    geocoding_user_agent: str = Field(default="sentinelai-project", env="GEOCODING_USER_AGENT")
    embedding_model_name: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL_NAME")

    # Incident matching settings (no prefix needed if shared)
    time_window_minutes: int = Field(default=60, env="TIME_WINDOW_MINUTES")
    distance_threshold_km: float = Field(default=1.0, env="DISTANCE_THRESHOLD_KM")
    similarity_threshold: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    content_similarity_min_common_words: int = Field(default=2, env="CONTENT_SIMILARITY_MIN_COMMON_WORDS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'
    )

settings = Settings()