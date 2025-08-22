import google.generativeai as genai
from openai import OpenAI
from config.settings import settings

class LLMService:
    """
    A singleton class to manage the LLM client with lazy loading.
    This prevents the app from crashing on startup if keys are not configured.
    """
    def __init__(self):
        self._client = None
        self._provider = None
        # Load initial provider from settings, but don't initialize client
        self.reload()

    def _initialize_client(self):
        """Initializes the client based on current settings. Called on first use."""
        print(f"IDX Agent: Lazily initializing LLM client for provider '{self._provider}'...")
        if self._provider == 'google':
            if not settings.google_api_key:
                raise ValueError("GOOGLE_API_KEY is not configured for the IDX agent.")
            genai.configure(api_key=settings.google_api_key)
            return genai.GenerativeModel(settings.google_model_name)
        
        elif self._provider == 'openai':
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is not configured for the IDX agent.")
            return OpenAI(api_key=settings.openai_api_key)

        elif self._provider == 'local':
            if not settings.local_llm_url:
                raise ValueError("LOCAL_LLM_URL is not configured for the IDX agent.")
            return OpenAI(base_url=settings.local_llm_url, api_key="not-needed")
            
        else:
            raise ValueError(f"Unsupported LLM provider: {self._provider}")

    def get_client(self):
        """Gets the initialized client, creating it if it doesn't exist."""
        if self._client is None:
            self._client = self._initialize_client()
        return self._client
        
    def get_provider(self):
        return self._provider

    def is_configured(self):
        """Checks if the necessary API key for the current provider is set."""
        if self._provider == 'google':
            return bool(settings.google_api_key)
        if self._provider == 'openai':
            return bool(settings.openai_api_key)
        if self._provider == 'local':
            return bool(settings.local_llm_url)
        return False

    def reload(self):
        """Resets the client, forcing re-initialization on next use. Useful after settings change."""
        print("IDX Agent: Reloading LLM configuration.")
        self._client = None
        self._provider = settings.llm_provider.lower()

# Singleton instance
_llm_service_instance = LLMService()

def get_llm_service():
    """Provides access to the singleton LLM service instance."""
    return _llm_service_instance