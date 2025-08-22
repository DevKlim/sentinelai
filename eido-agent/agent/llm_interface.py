import json
import google.generativeai as genai
from openai import OpenAI
from config.settings import settings

class LLMInterface:
    def __init__(self):
        self.provider = settings.llm_provider.lower()
        self.client = None  # Initialize to None for lazy loading
        print(f"EIDO Agent: LLMInterface created for provider: {self.provider}. Client will be initialized on first use.")

    def _get_client(self):
        """Lazily initializes and returns the LLM client."""
        if self.client is None:
            print("EIDO Agent: First use or after settings change: Initializing LLM client...")
            self.client = self._initialize_client()
        return self.client

    def _initialize_client(self):
        """Initializes the appropriate LLM client based on settings."""
        if self.provider == 'google':
            if not settings.google_api_key:
                return None
            genai.configure(api_key=settings.google_api_key)
            return genai.GenerativeModel(settings.google_model_name)
        
        elif self.provider == 'openai':
            if not settings.openai_api_key:
                return None
            return OpenAI(api_key=settings.openai_api_key)
            
        else:
            return None

    def generate_content(self, prompt: str) -> str:
        """Generates text content using the configured LLM."""
        client = self._get_client()
        if not client:
            raise RuntimeError(f"EIDO Agent: LLM client for provider '{self.provider}' could not be initialized.")
        try:
            if self.provider == 'google':
                return client.generate_content(prompt).text
            elif self.provider == 'openai':
                return client.chat.completions.create(
                    model=settings.openai_model_name,
                    messages=[{"role": "user", "content": prompt}],
                ).choices[0].message.content
            # This line is unreachable if client is valid and provider is one of the above.
            # If client is None, the RuntimeError is raised.
            # If provider is unsupported, _initialize_client returns None, leading to RuntimeError.
        except Exception as e:
            return f"Error: Could not get response from LLM. Details: {e}"

    def _clean_json_response(self, response_text: str) -> dict:
        """Helper to clean and parse JSON from LLM response."""
        try:
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

    def fill_eido_template(self, template: dict, scenario_description: str, rag_context: str = "") -> dict:
        """Generates a JSON object by populating a template from raw text, guided by RAG context."""
        template_str = json.dumps(template, indent=2)

        context_instructions = ""
        if rag_context:
            context_instructions = f"""
        **SCHEMA DOCUMENTATION (Use this for accuracy):**
        Use the following context from the EIDO OpenAPI schema and documentation to understand the available fields, their purpose, required data types, and correct structure. Adhere strictly to this documentation when filling the template.
        ---
        {rag_context}
        ---
        """
        prompt = f"""
        You are a meticulous public safety data analyst. Your task is to analyze an incident description and populate a detailed EIDO (Emergency Incident Data Object) JSON template with extracted information.
        {context_instructions}
        **CRITICAL INSTRUCTIONS:**

        1.  **Populate the JSON Template**: Fill every field in the provided JSON template using details from the text. This includes filling in all `"comment"` fields with a brief, relevant description of that object's purpose or content.

        2.  **Extract All Key Details & ADD to Components**:
            -   **WHAT**: The core event. Populate `notes-what-summary`.
            -   **WHERE**: The location. Populate the `locationComponent`.
            -   **WHEN/DATE/MOTIVE/STATUS**: Populate the `notes-when-motive-status` note.
            -   **PEOPLE (Victims, Suspects, Witnesses)**: For EACH person mentioned, ADD a new object to the `personComponent` array. Set `personIncidentRoleRegistryText` to `["Victim"]`, `["Suspect"]`, or `["Witness"]`. Fill their name, age, and a detailed physical description in `ncPersonComponent`.
            -   **RESOURCES**: For EACH responding unit mentioned (e.g., "Engine 5", "Patrol car 2A33"), ADD a new object to the `emergencyResourceComponent` array if it exists in the template. Include `emergencyResourceName` and `secondaryUnitStatusRegistryText`.
            -   **ITEMS/VEHICLES**: For EACH key item (e.g., weapons, evidence) or vehicle involved, ADD a new object to the `itemComponent` or `vehicleComponent` array respectively if they exist in the template. Describe the item within `ncItemType`.
            -   **PRIORITY**: Based on the severity, set `incidentCommonPriorityNumber` from 1 (highest) to 5 (lowest).

        3.  **Generate Metadata**:
            -   Create a descriptive, headline-style incident name (e.g., "Shooting at The Owl Bar"). Add this as a new key `suggestedIncidentName` at the root of the JSON object.
            -   Generate a list of 3-5 relevant keyword tags (e.g., "shooting", "homicide", "bar", "weapon"). Add this as a new key `tags` at the root of the JSON object.

        4.  **Geocode**: If a physical address is described, geocode it and populate `latitude` and `longitude`. If not possible, use `null`.

        5.  **Clean Up**: Remove any placeholder objects (like `person-suspect-placeholder`) from component arrays after you have added the actual people/items found in the text. If no relevant entities are found, leave the array empty.

        **JSON TEMPLATE:**
        ```json
        {template_str}
        ```

        **INCIDENT DESCRIPTION:**
        ---
        {scenario_description}
        ---

        Your response MUST be ONLY the final, valid JSON object. Do not include any explanatory text, markdown formatting, or anything outside the JSON object itself.
        """
        response_text = self.generate_content(prompt)
        return self._clean_json_response(response_text)

    def reload(self):
        """Re-initializes the client. Useful when settings change."""
        print("EIDO Agent: Reloading LLMInterface client...")
        # Re-read the provider from the (potentially updated) settings
        self.provider = settings.llm_provider.lower()
        # Reset client to None so it gets re-initialized on next use
        self.client = None

llm_interface = LLMInterface()