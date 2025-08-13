import threading
import asyncio
import httpx
import json
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2

from config.settings import settings
from services.llm_service import get_llm_client

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points
    on the earth (specified in decimal degrees).
    """
    if None in [lat1, lon1, lat2, lon2]:
        return float('inf')
        
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    r = 6371  # Radius of earth in kilometers.
    return c * r

class IncidentCategorizer:
    def __init__(self):
        self.eido_agent_url = settings.eido_agent_url
        try:
            self.llm_client, self.llm_provider = get_llm_client()
        except ValueError as e:
            print(f"LLM client not configured, categorizer will be inactive: {e}")
            self.llm_client = None
            self.llm_provider = None
        self.check_interval = 30 # Check every 30 seconds
        self.time_window_hours = 4  # Time window for algorithmic matching
        self.distance_threshold_km = 5 # Distance threshold for algorithmic matching

    async def fetch_uncategorized_eidos(self):
        """Fetches EIDOs marked as 'uncategorized' from the EIDO agent."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.eido_agent_url}/api/v1/eidos?status=uncategorized")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error fetching uncategorized EIDOs: {e.response.text}")
            return []
        except httpx.RequestError as e:
            print(f"Could not connect to EIDO agent: {e}")
            return []

    async def fetch_active_incidents(self):
        """Fetches active ('open') incidents from the EIDO agent."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.eido_agent_url}/api/v1/incidents?status=open")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error fetching active incidents: {e.response.text}")
            return []
        except httpx.RequestError as e:
            print(f"Could not connect to EIDO agent to fetch active incidents: {e}")
            return []

    def find_potential_matches(self, new_eido, active_incidents):
        """Algorithmically filters active incidents to find potential matches based on time and location."""
        potential_matches = []
        new_eido_location = new_eido.get("location")
        new_eido_time_str = new_eido.get("timestamp")

        if not new_eido_location or not isinstance(new_eido_location, dict) or not new_eido_time_str:
            return []
        
        new_lat = new_eido_location.get('latitude')
        new_lon = new_eido_location.get('longitude')
        
        if new_lat is None or new_lon is None:
             return []

        try:
            new_time = datetime.fromisoformat(new_eido_time_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            print(f"Invalid timestamp format for EIDO {new_eido.get('eido_id')}: {new_eido_time_str}")
            return []

        for incident in active_incidents:
            try:
                incident_time = datetime.fromisoformat(incident.get('created_at').replace('Z', '+00:00'))
                if abs((new_time - incident_time).total_seconds()) > self.time_window_hours * 3600:
                    continue
            except (ValueError, TypeError):
                continue # Skip incident if it has invalid time

            for loc in incident.get("locations", []):
                if isinstance(loc, list) and len(loc) == 2:
                    dist = haversine(new_lat, new_lon, loc[0], loc[1])
                    if dist <= self.distance_threshold_km:
                        potential_matches.append(incident)
                        break
        return potential_matches

    async def get_incident_match_from_llm(self, new_eido, candidate_incidents):
        """Asks LLM to classify EIDO against candidate incidents."""
        if not self.llm_client or not candidate_incidents:
            return None

        prompt_header = f"""
        You are an intelligent incident correlation agent. Your task is to determine if a new emergency report (EIDO) belongs to an existing active incident.

        Here is the new EIDO report:
        - EIDO ID: {new_eido.get('eido_id')}
        - Description: "{new_eido.get('description', 'No description provided.')}"
        - Timestamp: {new_eido.get('timestamp')}
        - Location: {new_eido.get('location')}

        Below is a list of potentially related active incidents. These were pre-filtered based on time and location. Review them and decide if the new EIDO is an update to one of them or represents a completely new incident.
        """

        incident_summaries = ""
        for i, incident in enumerate(candidate_incidents):
            incident_summaries += f"""
            ---
            Candidate Incident {i+1}:
            - Incident ID: {incident.get('incident_id')}
            - Incident Name: "{incident.get('name')}"
            - Incident Type: "{incident.get('incident_type')}"
            - Incident Summary: "{incident.get('summary')}"
            - Tags: {', '.join(incident.get('tags', []))}
            - Created At: {incident.get('created_at')}
            ---
            """
        
        prompt_footer = f"""
        Analyze the new EIDO against the candidate incidents. Consider factors like event type, location proximity, time proximity, and details in the descriptions and tags.

        Respond with a JSON object with one of the following structures:

        1. If the new EIDO matches an existing incident, use this format:
        {{
            "decision": "MATCH",
            "incident_id": "the_id_of_the_matching_incident",
            "reason": "A brief explanation for why it's a match."
        }}

        2. If the new EIDO does NOT match any of the candidates and should be a new incident, use this format:
        {{
            "decision": "NEW",
            "reason": "A brief explanation for why it's a new incident.",
            "incident_details": {{
                "incident_name": "A concise name for the new incident (e.g., 'Vehicle Collision on I-5').",
                "incident_type": "A general category (e.g., 'Fire', 'Medical Emergency', 'Traffic Accident').",
                "summary": "A brief summary of the new incident based on the EIDO text.",
                "tags": ["tag1", "tag2"]
            }}
        }}

        Your JSON response:
        """
        prompt = prompt_header + incident_summaries + prompt_footer

        try:
            if self.llm_provider == 'google':
                response = self.llm_client.generate_content(prompt)
                clean_response = response.text.strip().replace("```json", "").replace("```", "").strip()
                return json.loads(clean_response)
            else: # OpenAI or local
                response = self.llm_client.completions.create(
                    model=settings.openai_model_name if self.llm_provider == 'openai' else "local-model",
                    messages=[{{"role": "user", "content": prompt}}],
                    response_format={{"type": "json_object"}},
                )
                return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"LLM matching failed: {e}\nPrompt was: {prompt}")
            return None

    async def create_new_incident_from_eido(self, eido: dict):
        """Generates incident details from an EIDO and links it to a new incident."""
        print(f"Generating details for a new incident from EIDO {eido.get('eido_id')}")
        prompt = f"""
        Analyze the following EIDO text and determine the incident details.
        EIDO Text: "{eido.get('description', '')}"

        Based on the text, provide the following in JSON format:
        - incident_name: A concise name for the incident (e.g., "Structure Fire on Main St").
        - incident_type: A general category (e.g., "Fire", "Medical Emergency", "Traffic Accident").
        - summary: A brief summary of the incident.
        - tags: A list of 1-3 relevant keywords or tags (e.g., ["fire", "downtown", "high-rise"]).
        """
        try:
            if self.llm_provider == 'google':
                response = self.llm_client.generate_content(prompt)
                clean_response = response.text.strip().replace("```json", "").replace("```", "").strip()
                categorized_details = json.loads(clean_response)
            else: # OpenAI or local
                response = self.llm_client.completions.create(
                    model=settings.openai_model_name if self.llm_provider == 'openai' else "local-model",
                    messages=[{{"role": "user", "content": prompt}}],
                    response_format={{"type": "json_object"}},
                )
                categorized_details = json.loads(response.choices[0].message.content)
            
            if categorized_details:
                await self.link_eido_to_new_incident(eido["eido_id"], categorized_details)
        except Exception as e:
            print(f"LLM categorization for new incident failed: {e}")

    async def link_eido_to_new_incident(self, eido_id: str, incident_details: dict):
        """Links an EIDO to a NEW incident in the EIDO agent."""
        incident_details['status'] = 'open'
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.eido_agent_url}/api/v1/incidents/link_eido",
                    json={"eido_id": eido_id, "incident_details": incident_details},
                    timeout=30.0
                )
                response.raise_for_status()
                print(f"Successfully created new incident and linked EIDO {eido_id}.")
                return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Failed to link EIDO {eido_id} to new incident: {e.response.text}")
        except httpx.RequestError as e:
            print(f"Connection error when linking EIDO {eido_id} to new incident: {e}")
        return None
    
    async def link_eido_to_existing_incident(self, eido_id: str, incident_id: str):
        """Links an EIDO to an EXISTING incident in the EIDO agent."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.eido_agent_url}/api/v1/incidents/link_eido",
                    json={"eido_id": eido_id, "incident_id": incident_id},
                    timeout=30.0
                )
                response.raise_for_status()
                print(f"Successfully linked EIDO {eido_id} to existing incident {incident_id}.")
                return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Failed to link EIDO {eido_id} to existing incident {incident_id}: {e.response.text}")
        except httpx.RequestError as e:
            print(f"Connection error when linking EIDO {eido_id} to existing incident {incident_id}: {e}")
        return None

    async def process_eido(self, eido: dict):
        """
        Categorizes an EIDO by matching it against active incidents or creating a new one.
        """
        active_incidents = await self.fetch_active_incidents()
        potential_matches = self.find_potential_matches(eido, active_incidents)

        llm_decision = None
        if potential_matches:
            print(f"Found {len(potential_matches)} potential matches for EIDO {eido.get('eido_id')}. Querying LLM.")
            llm_decision = await self.get_incident_match_from_llm(eido, potential_matches)
        
        if llm_decision:
            if llm_decision.get("decision") == "MATCH":
                incident_id = llm_decision.get("incident_id")
                print(f"LLM Decision: MATCH EIDO {eido['eido_id']} with incident {incident_id}. Reason: {llm_decision.get('reason')}")
                await self.link_eido_to_existing_incident(eido["eido_id"], incident_id)
                return
            elif llm_decision.get("decision") == "NEW":
                print(f"LLM Decision: NEW incident for EIDO {eido['eido_id']}. Reason: {llm_decision.get('reason')}")
                incident_details = llm_decision.get("incident_details")
                if incident_details:
                    await self.link_eido_to_new_incident(eido["eido_id"], incident_details)
                else:
                    # Fallback if LLM says NEW but provides no details
                    await self.create_new_incident_from_eido(eido) 
                return

        # Fallback: No potential matches, or LLM failed/decided it's new without providing details
        print(f"No definitive match for EIDO {eido['eido_id']}. Creating a new incident via fallback.")
        await self.create_new_incident_from_eido(eido)

    async def run(self, stop_event: threading.Event):
        """Periodically checks for and categorizes uncategorized EIDOs."""
        if not self.llm_client:
            print("Categorizer is not running because the LLM client is not configured.")
            return

        while not stop_event.is_set():
            print("IDX Categorizer: Checking for uncategorized EIDOs...")
            eidos = await self.fetch_uncategorized_eidos()
            if not eidos:
                print("IDX Categorizer: No new EIDOs found.")

            for eido in eidos:
                if stop_event.is_set():
                    break
                print(f"IDX Categorizer: Processing EIDO {eido.get('eido_id')}")
                await self.process_eido(eido)
            
            # Sleep until next check
            for _ in range(self.check_interval):
                if stop_event.is_set():
                    break
                await asyncio.sleep(1)

def run_categorizer(stop_event: threading.Event):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    categorizer = IncidentCategorizer()
    loop.run_until_complete(categorizer.run(stop_event=stop_event))