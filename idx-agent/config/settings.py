from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    eido_agent_url: str = "http://eido_api:8000"

settings = Settings()