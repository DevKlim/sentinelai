# sentinelai/eido-agent/agent/llm_interface.py
import json
import os
import google.generativeai as genai
from openai import OpenAI
from config.settings import settings
from services.schema_service import schema_service # Import the service instance

class LLMInterface:
    def __init__(self):
        self.provider = settings.llm_provider.lower()
        self.client = None
        self.schema_service = schema_service # Use the singleton instance
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
            if not settings.google_api_key: return None
            genai.configure(api_key=settings.google_api_key)
            return genai.GenerativeModel(settings.google_model_name)
        elif self.provider == 'openai':
            if not settings.openai_api_key: return None
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
                generation_config = genai.types.GenerationConfig(temperature=0.7, top_p=0.95, top_k=40)
                response = client.generate_content(prompt, generation_config=generation_config)
                return response.text
            elif self.provider == 'openai':
                return client.chat.completions.create(
                    model=settings.openai_model_name,
                    messages=[{"role": "user", "content": prompt}],
                ).choices[0].message.content
            return f"Error: Unsupported provider '{self.provider}'"
        except Exception as e:
            print(f"EIDO Agent: Error during LLM content generation: {e}")
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

    def fill_eido_template(self, event_type: str, scenario_description: str) -> dict:
        """Generates a JSON object by populating a template from raw text, guided by the event type."""
        template = self.schema_service.get_template_for_event_type(event_type)
        if not template:
            return {"error": f"Could not load base template for event type '{event_type}'."}
        template_str = json.dumps(template, indent=2)
        
        component_docs = ""
        for component_name in template.keys():
            component_docs += self.schema_service.get_documentation_for_component(component_name) + "\n\n"

        prompt = f"""
        You are a meticulous public safety data analyst. Your task is to analyze an incident description and populate a detailed EIDO (Emergency Incident Data Object) JSON template with extracted information.
        
        **SCHEMA DOCUMENTATION (Use this for accuracy):**
        Use the following context from the EIDO OpenAPI schema and documentation to understand the available fields, their purpose, required data types, and correct structure. Adhere strictly to this documentation when filling the template.
        ---
        {component_docs}
        ---
        
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

    def generate_eido_template_from_description(self, event_type: str, description: str) -> dict:
        """Generates a new EIDO template from a description, using the event type to guide the process."""
        template = self.schema_service.get_template_for_event_type(event_type)
        if not template:
            return {"error": f"Could not load base template for event type '{event_type}'."}
        template_str = json.dumps(template, indent=2)
        
        component_docs = ""
        for component_name in template.keys():
            component_docs += self.schema_service.get_documentation_for_component(component_name) + "\n\n"

        prompt = f"""
        You are an expert in creating structured data schemas for public safety. Your task is to generate a valid EIDO (Emergency Incident Data Object) JSON template based on a user's natural language description.

        **SCHEMA DOCUMENTATION (Use this for accuracy):**
        Use the following context from the EIDO OpenAPI schema and documentation to understand the available fields, their purpose, required data types, and correct structure. Adhere strictly to this documentation when building the template.
        ---
        {component_docs}
        ---
        **CRITICAL INSTRUCTIONS:**
        1.  **Analyze the Description**: Understand the type of incident the user wants to model (e.g., "a fire incident," "a traffic accident with injuries," "a theft report").
        2.  **Select Relevant Components**: Choose the most appropriate EIDO components from the documentation (e.g., `incidentComponent`, `personComponent`, `vehicleComponent`, `locationComponent`).
        3.  **Include Placeholders**: The template should contain placeholder values that clearly indicate what kind of information should be filled in later. For example, use strings like "[Enter detailed description here]" or `null` for values that will be populated dynamically.
        4.  **Add Comments**: Add a `"comment"` field to each major component and object in the JSON, explaining its purpose. This is crucial for usability.
        5.  **Valid JSON**: The final output MUST be a single, valid JSON object and nothing else. Do not include any explanatory text, markdown formatting, or anything outside the JSON object itself.

        **USER'S DESCRIPTION OF THE DESIRED TEMPLATE:**
        ---
        {description}
        ---

        Now, generate the complete EIDO JSON template based on the user's description, using the documentation provided as your guide. You may use the following as a structural hint, but prioritize the user's description and the documentation:
        ```json
        {template_str}
        ```
        """
        response_text = self.generate_content(prompt)
        return self._clean_json_response(response_text)

    def modify_eido_with_updates(self, original_eido: dict, updates_description: str) -> dict:
        """
        Takes an existing EIDO and a natural language description of updates,
        and returns a modified EIDO.
        """
        original_eido_str = json.dumps(original_eido, indent=2)
        schema_context = self.schema_service.get_documentation_for_component("EmergencyIncidentDataObjectType")

        prompt = f"""
        You are a meticulous public safety data analyst. Your task is to update an existing EIDO (Emergency Incident Data Object) JSON based on a list of changes provided by an operator.

        **EIDO SCHEMA CONTEXT:**
        ---
        {schema_context}
        ---

        **CRITICAL INSTRUCTIONS:**
        1.  **Analyze the Original EIDO**: Understand the existing structure and content of the provided JSON.
        2.  **Apply the Updates**: Carefully read the operator's updates and modify the original EIDO to reflect these changes. This may involve changing values, adding new objects to arrays (like new victims to `personComponent`), or removing objects. For example, if asked to change the number of victims to 2, ensure the `personComponent` array contains exactly two objects with the role "Victim".
        3.  **Maintain Schema Integrity**: The final output MUST be a valid JSON object that conforms to the EIDO structure described in the context. Do not add new top-level keys that are not part of the EIDO schema unless they are `suggestedIncidentName` or `tags`.
        4.  **Preserve Existing Data**: Only change the data specified in the updates. All other data in the original EIDO must be preserved.
        5.  **Output**: Your response MUST be ONLY the final, complete, valid JSON object. Do not include any explanatory text, markdown formatting, or anything outside the JSON object itself.

        **ORIGINAL EIDO JSON:**
        ```json
        {original_eido_str}
        ```

        **OPERATOR'S UPDATES:**
        ---
        {updates_description}
        ---

        Now, generate the single, complete, updated EIDO JSON.
        """
        response_text = self.generate_content(prompt)
        return self._clean_json_response(response_text)

    def reload(self):
        """Re-initializes the client. Useful when settings change."""
        print("EIDO Agent: Reloading LLMInterface client...")
        self.provider = settings.llm_provider.lower()
        self.client = None

llm_interface = LLMInterface()