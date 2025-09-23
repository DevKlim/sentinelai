import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    """
    Pydantic settings for the Geocoding agent.
    Values are automatically read from environment variables.
    """
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8002, env="API_PORT")

    # LLM Provider settings with GEOCODING_ prefix
    llm_provider: str = Field(default="google", env="GEOCODING_LLM_PROVIDER")
    
    google_api_key: Optional[str] = Field(default=None, env="GEOCODING_GOOGLE_API_KEY")
    google_model_name: str = Field(default="gemini-1.5-flash-latest", env="GEOCODING_GOOGLE_MODEL_NAME")

    openai_api_key: Optional[str] = Field(default=None, env="GEOCODING_OPENAI_API_KEY")
    openai_model_name: str = Field(default="gpt-4o", env="GEOCODING_OPENAI_MODEL_NAME")
    
    openrouter_api_key: Optional[str] = Field(default=None, env="GEOCODING_OPENROUTER_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'
    )

settings = Settings()
