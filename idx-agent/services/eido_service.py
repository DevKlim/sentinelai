import json
import os
from uuid import uuid4

class EidoService:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def get_all_incidents(self):
        incidents = []
        for filename in os.listdir(self.data_dir):
            if filename.endswith(".json"):
                with open(os.path.join(self.data_dir, filename), "r") as f:
                    incidents.append(json.load(f))
        return incidents

    def get_incident(self, incident_id):
        filepath = os.path.join(self.data_dir, f"{incident_id}.json")
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return json.load(f)
        return None

    def create_incident(self, incident_text):
        incident_id = str(uuid4())
        incident = {
            "id": incident_id,
            "text": incident_text,
            "status": "new"
        }
        with open(os.path.join(self.data_dir, f"{incident_id}.json"), "w") as f:
            json.dump(incident, f)
        return incident

    def correlate_incidents(self, incident_text):
        # Basic keyword matching for correlation
        incidents = self.get_all_incidents()
        for incident in incidents:
            if incident["text"] in incident_text or incident_text in incident["text"]:
                return {"correlation_id": incident["id"], "status": "update"}
        
        return {"correlation_id": None, "status": "new"}


    def process_eido(self, eido_data):
        try:
            # Decode bytes to string before loading as JSON
            eido_string = eido_data.decode('utf-8')
            eido_json = json.loads(eido_string)
            incident_text = eido_json.get("description", "No description provided.")
            
            correlation = self.correlate_incidents(incident_text)
            
            if correlation["status"] == "new":
                self.create_incident(incident_text)
            else:
                # For now, we just log the update. A more sophisticated update
                # mechanism would be needed for a real application.
                print(f"Incident {correlation['correlation_id']} updated.")
        except json.JSONDecodeError:
            print("Error decoding EIDO JSON.")
        except UnicodeDecodeError:
            print("Error decoding file data. Make sure the file is UTF-8 encoded.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
