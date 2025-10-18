import threading
import asyncio
import httpx
import json
import os
from datetime import datetime, timezone
from math import radians, sin, cos, sqrt, atan2
from services.llm_service import llm_service
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
        self.eido_agent_url = os.environ.get("EIDO_API_URL", "http://python-services:8000")
        self.check_interval = settings.categorizer_interval_seconds
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
            try:
                incident_time_str = incident.get('created_at')
                if not incident_time_str: continue
                incident_time = datetime.fromisoformat(incident_time_str.replace('Z', '+00:00'))
                if abs((new_time - incident_time).total_seconds()) > self.time_window_hours * 3600:
                    continue
            except (ValueError, TypeError, AttributeError): continue

            for loc in incident.get("locations", []):
                if isinstance(loc, list) and len(loc) == 2:
                    dist = haversine(new_lat, new_lon, loc[0], loc[1])
                    if dist <= self.distance_threshold_km:
                        is_match = True
                        break
            if not is_match: continue

            incident_text = f"{incident.get('name', '')} {incident.get('summary', '')} {' '.join(incident.get('tags', []))}"
            if text_similarity(new_eido_desc, incident_text) < self.similarity_threshold:
                continue

            potential_matches.append(incident)
        return potential_matches

    async def get_incident_match_from_llm(self, new_eido, candidate_incidents):
        """Asks LLM to classify EIDO against candidate incidents."""
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
        {{"decision": "MATCH", "incident_id": "the_id_of_the_matching_incident", "reason": "Briefly explain the match."}}

        If it's a NEW incident, use this format:
        {{"decision": "NEW", "reason": "Briefly explain why it's a new incident.", "incident_details": {{"incident_name": "A concise, descriptive name for the new incident.", "incident_type": "Categorize as 'Fire', 'Medical', 'Traffic', 'Crime', or 'Other'.", "summary": "A brief summary of the new incident.", "tags": ["relevant", "keywords"]}}}}

        Your JSON response:
        """
        try:
            response_text = llm_service.generate_content(prompt, is_json=True)
            return json.loads(response_text)
        except Exception as e:
            print(f"LLM matching failed: {e}")
            return None

    async def create_new_incident_details(self, eido: dict):
        """Uses LLM to generate details for a new incident from an EIDO."""
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
            response_text = llm_service.generate_content(prompt, is_json=True)
            return json.loads(response_text)
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
            print(f"No definitive match for EIDO {eido['id']}. Creating new incident via fallback.")
            new_details = await self.create_new_incident_details(eido)
            if new_details:
                await self.link_eido_to_incident(eido_id=eido["id"], incident_details=new_details)

    async def run(self, stop_event: threading.Event):
        """Periodically checks for and categorizes uncategorized EIDOs."""
        while not stop_event.is_set():
            if llm_service.client is None:
                print("Categorizer is paused: LLM client not configured. Retrying in 60s.")
                await asyncio.sleep(60)
                continue

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

class _CategorizerThreadManager:
    def __init__(self):
        self.thread = None
        self.stop_event = threading.Event()
        self.flag_file = "categorizer_enabled.flag"

    def is_enabled(self):
        return os.path.exists(self.flag_file)

    def set_enabled(self, enable: bool):
        if enable:
            if not os.path.exists(self.flag_file):
                open(self.flag_file, 'a').close()
        else:
            if os.path.exists(self.flag_file):
                os.remove(self.flag_file)

    def start(self):
        if self.is_enabled() and (self.thread is None or not self.thread.is_alive()):
            print("Starting categorizer thread...")
            self.stop_event.clear()
            self.thread = threading.Thread(target=run_categorizer, args=(self.stop_event,), daemon=True)
            self.thread.start()

    def start_if_enabled(self):
        self.start()

    def stop(self):
        if self.thread and self.thread.is_alive():
            print("Stopping categorizer thread...")
            self.stop_event.set()
            self.thread.join(timeout=5)
            self.thread = None

    def get_status(self):
        status = "stopped"
        if self.thread and self.thread.is_alive():
            status = "running"
        return {"enabled": self.is_enabled(), "status": status}

# Singleton instance that can be imported by other modules
categorizer_thread = _CategorizerThreadManager()
