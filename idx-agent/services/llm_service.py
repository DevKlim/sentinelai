import google.generativeai as genai
from openai import OpenAI
from config.settings import settings

def get_llm_client():
    """
    Initializes and returns the appropriate LLM client based on the .env configuration.
    """
    provider = settings.llm_provider.lower()

    if provider == 'google':
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is not set in the .env file.")
        genai.configure(api_key=settings.google_api_key)
        model = genai.GenerativeModel(settings.google_model_name)
        return model, provider
        
    elif provider == 'openai':
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set in the .env file.")
        client = OpenAI(api_key=settings.openai_api_key)
        return client, provider

    elif provider == 'local':
        if not settings.local_llm_url:
            raise ValueError("LOCAL_LLM_URL is not set in the .env file.")
        # This is a generic client for local LLMs, assuming an OpenAI-compatible API
        client = OpenAI(base_url=settings.local_llm_url, api_key="not-needed")
        return client, provider
        
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")