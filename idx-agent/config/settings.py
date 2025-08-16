from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """
    Pydantic settings class to manage environment variables.
    By default, it automatically reads from environment variables.
    """
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    # <-- CORRECTED LINE: Default to localhost for intra-container communication
    eido_agent_url: str = "http://localhost:8000"
    
    # LLM Provider: 'google', 'openai', or 'local'
    llm_provider: str = Field(default='google', env='LLM_PROVIDER')
    
    # API Keys - will be loaded from environment
    google_api_key: str | None = Field(default=None, env='GOOGLE_API_KEY')
    openai_api_key: str | None = Field(default=None, env='OPENAI_API_KEY')
    
    # Model Names
    google_model_name: str = Field(default='gemini-2.5-flash-lite', env='GOOGLE_MODEL_NAME')
    openai_model_name: str = Field(default='gpt-4o', env='OPENAI_MODEL_NAME')
    local_llm_url: str | None = Field(default=None, env='LOCAL_LLM_URL')

settings = Settings()