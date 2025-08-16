# sdsc-orchestrator/eido-agent/agent/llm_interface.py
import json
import google.generativeai as genai
from openai import OpenAI
from config.settings import settings

class LLMInterface:
    def __init__(self):
        self.provider = settings.llm_provider.lower()
        self.client = self._initialize_client()
        if not self.client:
            # We don't raise an error here, to allow the app to start
            # even if the LLM is not configured. Calls will fail later.
            print(f"CRITICAL: LLM provider '{self.provider}' is not configured correctly. LLM-dependent features will fail.")
        else:
            print(f"LLMInterface initialized with provider: {self.provider}")

    def _initialize_client(self):
        """Initializes the appropriate LLM client based on settings."""
        if self.provider == 'google':
            if not settings.google_api_key:
                print("WARNING: LLM_PROVIDER is 'google' but GOOGLE_API_KEY is not set.")
                return None
            genai.configure(api_key=settings.google_api_key)
            return genai.GenerativeModel(settings.google_model_name)
        
        elif self.provider == 'openai':
            if not settings.openai_api_key:
                print("WARNING: LLM_PROVIDER is 'openai' but OPENAI_API_KEY is not set.")
                return None
            return OpenAI(api_key=settings.openai_api_key)
            
        else:
            print(f"WARNING: Unsupported LLM provider specified: '{self.provider}'")
            return None

    def generate_content(self, prompt: str) -> str:
        """Generates text content using the configured LLM."""
        if not self.client:
            return "Error: LLM client is not initialized."
        try:
            if self.provider == 'google':
                response = self.client.generate_content(prompt)
                return response.text
            elif self.provider == 'openai':
                response = self.client.chat.completions.create(
                    model=settings.openai_model_name,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content
            return f"Error: Unsupported provider '{self.provider}'"
        except Exception as e:
            print(f"Error generating content with {self.provider}: {e}")
            return f"Error: Could not get response from LLM. Details: {e}"

    def generate_json_from_text(self, text: str, json_template: str) -> dict:
        """Generates a JSON object by populating a template from raw text."""
        prompt = f"""
        Analyze the following incident description and extract structured information to populate the given JSON template.
        The JSON template is:
        ```json
        {json_template}
        ```
        The incident description to analyze is:
        ---
        {text}
        ---
        Your response MUST be a valid JSON object that strictly follows the structure of the provided template. 
        Do not include any explanatory text, markdown formatting, or anything else outside of the JSON object itself.
        """
        response_text = self.generate_content(prompt)
        try:
            # Clean up potential markdown formatting from the LLM response
            clean_response = response_text.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            
            return json.loads(clean_response)
        except json.JSONDecodeError as e:
            print(f"Failed to decode LLM response into JSON: {e}")
            print(f"Raw LLM response was: {response_text}")
            return {"error": "Failed to generate valid JSON from text.", "raw_response": response_text}

# Create a singleton instance of the LLMInterface to be imported by other modules
llm_interface = LLMInterface()