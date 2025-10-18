import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional

class Settings(BaseSettings):
    """
    Pydantic settings for the IDX agent.
    Values are automatically read from environment variables.
    """
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # API settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8001, env="API_PORT")

    # Database connection URL
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")

    @field_validator('database_url')
    @classmethod
    def fix_database_url_scheme(cls, v: Optional[str]) -> Optional[str]:
        """Corrects the database scheme for SQLAlchemy asyncpg."""
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v and v.startswith("postgresql://") and "+asyncpg" not in v:
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # LLM Provider settings with IDX_ prefix
    llm_provider: str = Field(default="google", env="IDX_LLM_PROVIDER")
    
    google_api_key: Optional[str] = Field(default=None, env="IDX_GOOGLE_API_KEY")
    google_model_name: str = Field(default="gemini-1.5-flash-latest", env="IDX_GOOGLE_MODEL_NAME")

    openai_api_key: Optional[str] = Field(default=None, env="IDX_OPENAI_API_KEY")
    openai_model_name: str = Field(default="gpt-4o", env="IDX_OPENAI_MODEL_NAME")

    local_llm_url: Optional[str] = Field(default=None, env="IDX_LOCAL_LLM_URL")

    # Categorizer settings
    categorizer_interval_seconds: int = Field(default=10, env="CATEGORIZER_INTERVAL_SECONDS")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'
    )

settings = Settings()
