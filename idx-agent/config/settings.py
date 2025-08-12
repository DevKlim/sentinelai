from pydantic_settings import BaseSettings

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    api_host: str = "0.0.0.0"
    api_port: int = 8001
    eido_agent_url: str = "http://eido_api:8000"
    
    # LLM Provider: 'google', 'openai', or 'local'
    llm_provider: str = Field(default='google', env='LLM_PROVIDER')
    
    # API Keys - will be loaded from .env
    google_api_key: str | None = Field(default=None, env='GOOGLE_API_KEY')
    openai_api_key: str | None = Field(default=None, env='OPENAI_API_KEY')
    
    # Model Names
    google_model_name: str = Field(default='gemini-1.5-flash-latest', env='GOOGLE_MODEL_NAME')
    openai_model_name: str = Field(default='gpt-4o', env='OPENAI_MODEL_NAME')
    local_llm_url: str | None = Field(default=None, env='LOCAL_LLM_URL')

settings = Settings()




settings = Settings()