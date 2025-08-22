from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    """
    Pydantic settings class to manage environment variables for the IDX agent.
    """
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    eido_agent_url: str = "http://localhost:8000"
    
    # LLM Provider settings with IDX_ prefix
    llm_provider: str = Field(default='google', env='IDX_LLM_PROVIDER')
    
    google_api_key: Optional[str] = Field(default=None, env='IDX_GOOGLE_API_KEY')
    google_model_name: str = Field(default='gemini-1.5-flash-latest', env='IDX_GOOGLE_MODEL_NAME')
    
    openai_api_key: Optional[str] = Field(default=None, env='IDX_OPENAI_API_KEY')
    openai_model_name: str = Field(default='gpt-4o', env='IDX_OPENAI_MODEL_NAME')
    
    openrouter_api_key: Optional[str] = Field(default=None, env='IDX_OPENROUTER_API_KEY')
    
    local_llm_url: Optional[str] = Field(default=None, env='IDX_LOCAL_LLM_URL')

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'
    )

settings = Settings()