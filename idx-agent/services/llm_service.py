import google.generativeai as genai
from openai import OpenAI
from config.settings import settings
import json

class LLMService:
    def __init__(self):
        self.client = None
        self.provider = None
        self.reload() # Initial setup

    def _initialize_client(self):
        """Initializes the appropriate LLM client based on settings."""
        provider = settings.llm_provider.lower()
        self.provider = provider
        
        if provider == 'google':
            if not settings.google_api_key:
                print("IDX Agent Warning: GOOGLE_API_KEY is not set.")
                return None
            genai.configure(api_key=settings.google_api_key)
            return genai.GenerativeModel(settings.google_model_name)
        
        elif provider == 'openai':
            if not settings.openai_api_key:
                print("IDX Agent Warning: OPENAI_API_KEY is not set.")
                return None
            return OpenAI(api_key=settings.openai_api_key)

        elif provider == 'local':
            if not settings.local_llm_url:
                print("IDX Agent Warning: LOCAL_LLM_URL is not set.")
                return None
            return OpenAI(base_url=settings.local_llm_url, api_key="not-needed")
            
        else:
            print(f"IDX Agent Error: Unsupported LLM provider: {settings.llm_provider}")
            return None

    def generate_content(self, prompt: str, is_json: bool = False) -> str:
        """Generates text content using the configured LLM, abstracting the provider."""
        if self.client is None:
            raise RuntimeError(f"IDX Agent: LLM client for provider '{self.provider}' is not initialized.")
        try:
            if self.provider == 'google':
                generation_config = genai.types.GenerationConfig(
                    response_mime_type="application/json" if is_json else "text/plain",
                    temperature=0.2
                )
                response = self.client.generate_content(prompt, generation_config=generation_config)
                return response.text
            elif self.provider in ['openai', 'local']:
                response_format = {"type": "json_object"} if is_json else {"type": "text"}
                response = self.client.chat.completions.create(
                    model=settings.openai_model_name,
                    messages=[{"role": "user", "content": prompt}],
                    response_format=response_format,
                    temperature=0.2,
                )
                return response.choices[0].message.content
            raise NotImplementedError(f"Provider '{self.provider}' not supported.")
        except Exception as e:
            print(f"IDX Agent: Error during LLM content generation: {e}")
            raise

    def reload(self):
        """Re-initializes the client. Useful when settings change."""
        print("IDX Agent: Reloading LLMService client...")
        self.client = self._initialize_client()

# Singleton instance
llm_service = LLMService()
