import threading
import asyncio
import httpx
import json
from config.settings import settings
from services.llm_service import get_llm_client

class IncidentCategorizer:
    def __init__(self):
        self.eido_agent_url = settings.eido_agent_url
        try:
            self.llm_client, self.llm_provider = get_llm_client()
        except ValueError as e:
            print(f"LLM client not configured: {e}")
            self.llm_client = None
            self.llm_provider = None
        self.check_interval = 60

    async def fetch_uncategorized_eidos(self):
        """Fetches EIDOs marked as 'uncategorized' from the EIDO agent."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.eido_agent_url}/api/v1/eidos?status=uncategorized")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error fetching uncategorized EIDOs: {e.response.text}")
            return []
        except httpx.RequestError as e:
            print(f"Could not connect to EIDO agent: {e}")
            return []

    async def categorize_eido(self, eido: dict):
        """Uses an LLM to categorize an EIDO and determine incident details."""
        if not self.llm_client:
            return None

        eido_text = eido.get("description", "")
        if not eido_text:
            return None

        prompt = f"""
        Analyze the following EIDO text and determine the incident details.
        EIDO Text: "{eido_text}"

        Based on the text, provide the following in JSON format:
        - incident_name: A concise name for the incident (e.g., "Structure Fire on Main St").
        - incident_type: A general category (e.g., "Fire", "Medical Emergency", "Traffic Accident").
        - summary: A brief summary of the incident.
        """

        try:
            if self.llm_provider == 'google':
                response = self.llm_client.generate_content(prompt)
                return json.loads(response.text)
            else: # OpenAI or local
                response = self.llm_client.completions.create(
                    model=settings.openai_model_name if self.llm_provider == 'openai' else "local-model",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                )
                return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"LLM categorization failed: {e}")
            return None

    async def link_eido_to_incident(self, eido_id: str, incident_details: dict):
        """Links an EIDO to an existing or new incident in the EIDO agent."""
        # Add status to the incident details
        incident_details['status'] = 'open'
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.eido_agent_url}/api/v1/incidents/link_eido",
                    json={"eido_id": eido_id, "incident_details": incident_details},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Failed to link EIDO {eido_id}: {e.response.text}")
            return None

    async def run(self, stop_event: threading.Event):
        """Periodically checks for and categorizes uncategorized EIDOs."""
        if not self.llm_client:
            print("Categorizer is not running because the LLM client is not configured.")
            return

        while not stop_event.is_set():
            print("Checking for uncategorized EIDOs...")
            eidos = await self.fetch_uncategorized_eidos()
            for eido in eidos:
                if stop_event.is_set():
                    break
                categorized_details = await self.categorize_eido(eido)
                if categorized_details:
                    await self.link_eido_to_incident(eido["eido_id"], categorized_details)
            
            # Sleep for the check interval, but check for the stop event every second
            for _ in range(self.check_interval):
                if stop_event.is_set():
                    break
                await asyncio.sleep(1)

def run_categorizer(stop_event: threading.Event):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    categorizer = IncidentCategorizer()
    loop.run_until_complete(categorizer.run(stop_event=stop_event))
