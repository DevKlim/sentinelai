import threading
import asyncio
import httpx
import json
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
from services.llm_service import get_llm_client
from config.settings import settings

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two points on Earth."""
    if None in [lat1, lon1, lat2, lon2]:
        return float('inf')
    lon1, lat1, lon2, lat2 = map(radians, [float(lon1), float(lat1), float(lon2), float(lat2)])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    return 6371 * (2 * atan2(sqrt(a), sqrt(1 - a)))

def text_similarity(text1, text2):
    """Simple keyword overlap similarity."""
    if not text1 or not text2:
        return 0.0
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union) if union else 0.0

class IncidentCategorizer:
    def __init__(self):
        self.eido_agent_url = settings.eido_agent_url
        try:
            self.llm_client, self.llm_provider = get_llm_client()
        except ValueError as e:
            print(f"LLM client not configured, categorizer will be inactive: {e}")
            self.llm_client = None
        self.check_interval = 15  # Check every 15 seconds
        self.time_window_hours = 6
        self.distance_threshold_km = 10
        self.similarity_threshold = 0.1

    async def fetch_uncategorized_eidos(self):
        """Fetches EIDOs marked as 'uncategorized'."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.eido_agent_url}/api/v1/eidos?status=uncategorized")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Error fetching uncategorized EIDOs: {e}")
            return []

    async def fetch_active_incidents(self):
        """Fetches active ('open') incidents."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.eido_agent_url}/api/v1/incidents?status=open")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Error fetching active incidents: {e}")
            return []

    def find_potential_matches(self, new_eido, active_incidents):
        """Finds potential matches based on time, location, and text similarity."""
        potential_matches = []
        new_eido_loc = new_eido.get("location")
        new_eido_time_str = new_eido.get("timestamp")
        new_eido_desc = new_eido.get("description", "")

        if not new_eido_loc or not isinstance(new_eido_loc, dict) or not new_eido_time_str:
            return []
        
        new_lat, new_lon = new_eido_loc.get('latitude'), new_eido_loc.get('longitude')
        if new_lat is None or new_lon is None: return []

        try:
            new_time = datetime.fromisoformat(new_eido_time_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return []

        for incident in active_incidents:
            is_match = False
            # Time check
            try:
                # The incident's created_at will be a string in the JSON response
                incident_time = datetime.fromisoformat(incident.get('created_at').replace('Z', '+00:00'))
                if abs((new_time - incident_time).total_seconds()) > self.time_window_hours * 3600:
                    continue
            except (ValueError, TypeError, AttributeError): continue

            # Location check
            for loc in incident.get("locations", []):
                if isinstance(loc, list) and len(loc) == 2:
                    dist = haversine(new_lat, new_lon, loc[0], loc[1])
                    if dist <= self.distance_threshold_km:
                        is_match = True
                        break
            if not is_match: continue

            # Text similarity check
            incident_text = f"{incident.get('name', '')} {incident.get('summary', '')} {' '.join(incident.get('tags', []))}"
            if text_similarity(new_eido_desc, incident_text) < self.similarity_threshold:
                continue

            potential_matches.append(incident)
        return potential_matches

    async def get_incident_match_from_llm(self, new_eido, candidate_incidents):
        """Asks LLM to classify EIDO against candidate incidents."""
        if not self.llm_client or not candidate_incidents:
            return None

        prompt = f"""
        You are an intelligent incident correlation agent. Your task is to determine if a new emergency report (EIDO) belongs to an existing active incident.

        New EIDO Report:
        - Description: "{new_eido.get('description', 'N/A')}"
        - Timestamp: {new_eido.get('timestamp')}
        - Location: {new_eido.get('location')}

        Potentially Related Active Incidents:
        {json.dumps(candidate_incidents, indent=2, default=str)}

        Analyze the new EIDO against the candidates. Respond with a JSON object.
        
        If it's a MATCH, use this format:
        {{
            "decision": "MATCH",
            "incident_id": "the_id_of_the_matching_incident",
            "reason": "Briefly explain the match."
        }}

        If it's a NEW incident, use this format:
        {{
            "decision": "NEW",
            "reason": "Briefly explain why it's a new incident.",
            "incident_details": {{
                "incident_name": "A concise, descriptive name for the new incident.",
                "incident_type": "Categorize as 'Fire', 'Medical', 'Traffic', 'Crime', or 'Other'.",
                "summary": "A brief summary of the new incident.",
                "tags": ["relevant", "keywords"]
            }}
        }}

        Your JSON response:
        """
        try:
            # FIX: Use a default handler to convert datetimes to strings for JSON serialization
            prompt_payload = json.dumps(candidate_incidents, indent=2, default=str)
            
            # The full prompt construction remains the same
            full_prompt = f"""
            You are an intelligent incident correlation agent. Your task is to determine if a new emergency report (EIDO) belongs to an existing active incident.

            New EIDO Report:
            - Description: "{new_eido.get('description', 'N/A')}"
            - Timestamp: {new_eido.get('timestamp')}
            - Location: {new_eido.get('location')}

            Potentially Related Active Incidents:
            {prompt_payload}

            Analyze the new EIDO against the candidates. Respond with a JSON object.
            
            If it's a MATCH, use this format:
            {{
                "decision": "MATCH",
                "incident_id": "the_id_of_the_matching_incident",
                "reason": "Briefly explain the match."
            }}

            If it's a NEW incident, use this format:
            {{
                "decision": "NEW",
                "reason": "Briefly explain why it's a new incident.",
                "incident_details": {{
                    "incident_name": "A concise, descriptive name for the new incident.",
                    "incident_type": "Categorize as 'Fire', 'Medical', 'Traffic', 'Crime', or 'Other'.",
                    "summary": "A brief summary of the new incident.",
                    "tags": ["relevant", "keywords"]
                }}
            }}

            Your JSON response:
            """
            response = self.llm_client.generate_content(full_prompt)
            clean_response = response.text.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(clean_response)
        except Exception as e:
            print(f"LLM matching failed: {e}")
            return None

    async def create_new_incident_details(self, eido: dict):
        """Uses LLM to generate details for a new incident from an EIDO."""
        if not self.llm_client:
            return None
        prompt = f"""
        Analyze the following EIDO text and generate details for a new incident.
        EIDO Text: "{eido.get('description', '')}"

        Respond in JSON format with these fields:
        - incident_name: A concise, descriptive name for the new incident.
        - incident_type: Categorize as 'Fire', 'Medical', 'Traffic', 'Crime', or 'Other'.
        - summary: A brief summary of the incident.
        - tags: A list of 2-4 relevant keywords (tags).
        """
        try:
            response = self.llm_client.generate_content(prompt)
            clean_response = response.text.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(clean_response)
        except Exception as e:
            print(f"LLM detail generation for new incident failed: {e}")
            return None

    async def link_eido_to_incident(self, eido_id, incident_id=None, incident_details=None):
        """Links an EIDO to an incident or creates a new one in the EIDO agent."""
        payload = {"eido_id": eido_id}
        if incident_id:
            payload["incident_id"] = incident_id
        if incident_details:
            payload["incident_details"] = incident_details
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.eido_agent_url}/api/v1/incidents/link_eido",
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                print(f"Successfully linked EIDO {eido_id}. Response: {response.json()}")
        except Exception as e:
            print(f"Failed to link EIDO {eido_id}: {e}")

    async def process_eido(self, eido: dict):
        """Processes a single uncategorized EIDO."""
        active_incidents = await self.fetch_active_incidents()
        potential_matches = self.find_potential_matches(eido, active_incidents)

        llm_decision = None
        if potential_matches:
            print(f"Found {len(potential_matches)} potential matches for EIDO {eido.get('id')}. Querying LLM.")
            llm_decision = await self.get_incident_match_from_llm(eido, potential_matches)
        
        if llm_decision and llm_decision.get("decision") == "MATCH":
            incident_id = llm_decision.get("incident_id")
            print(f"LLM Decision: MATCH EIDO {eido['id']} with incident {incident_id}.")
            await self.link_eido_to_incident(eido_id=eido["id"], incident_id=incident_id)
        elif llm_decision and llm_decision.get("decision") == "NEW":
            print(f"LLM Decision: NEW incident for EIDO {eido['id']}.")
            await self.link_eido_to_incident(eido_id=eido["id"], incident_details=llm_decision.get("incident_details"))
        else:
            # Fallback: No matches or LLM failed
            print(f"No definitive match for EIDO {eido['id']}. Creating new incident via fallback.")
            new_details = await self.create_new_incident_details(eido)
            if new_details:
                await self.link_eido_to_incident(eido_id=eido["id"], incident_details=new_details)

    async def run(self, stop_event: threading.Event):
        """Periodically checks for and categorizes uncategorized EIDOs."""
        if not self.llm_client:
            print("Categorizer is not running: LLM client not configured.")
            return

        while not stop_event.is_set():
            print("IDX Categorizer: Checking for uncategorized EIDOs...")
            eidos = await self.fetch_uncategorized_eidos()
            if not eidos:
                print("IDX Categorizer: No new EIDOs found.")
            
            for eido in eidos:
                if stop_event.is_set(): break
                print(f"IDX Categorizer: Processing EIDO {eido.get('id')}")
                await self.process_eido(eido)
            
            await asyncio.sleep(self.check_interval)

def run_categorizer(stop_event: threading.Event):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    categorizer = IncidentCategorizer()
    try:
        loop.run_until_complete(categorizer.run(stop_event=stop_event))
    finally:
        loop.close()