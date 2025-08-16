import json
import requests
import time
import os
import sys

# Use the docker-compose service name for inter-container communication
EIDO_AGENT_URL = os.environ.get("EIDO_AGENT_URL", "http://python-services:8000")
IDX_AGENT_URL = os.environ.get("IDX_AGENT_URL", "http://python-services:8001")

def process_calls():
    processed_calls = []
    unprocessed_calls = []

    # Check if the data file exists
    if not os.path.exists("data/calls.jsonl"):
        print("data/calls.jsonl not found. Exiting.")
        return

    with open("data/calls.jsonl", "r") as f:
        for line in f:
            try:
                call = json.loads(line)
            except json.JSONDecodeError:
                print(f"Skipping malformed line: {line.strip()}")
                continue
            
            print(f"Processing call: {call.get('Call_ID', 'N/A')}")

            try:
                # FIX: The error "File name too long" with a JSON object as the filename
                # suggests the EIDO agent is misusing the 'scenario_description' field.
                # The error message also implies that the content of `call["Transcript"]`
                # is another JSON object string, instead of the raw transcript text.
                # This code now attempts to handle this nested structure to extract the
                # actual transcript text.
                scenario_text = call.get("Transcript", "")
                
                # Try to parse scenario_text in case it's a nested JSON string
                if isinstance(scenario_text, str):
                    try:
                        nested_data = json.loads(scenario_text)
                        if isinstance(nested_data, dict) and "Transcript" in nested_data:
                            scenario_text = nested_data.get("Transcript", "")
                    except json.JSONDecodeError:
                        # It's just a regular string, which is fine.
                        pass
                
                if not isinstance(scenario_text, str) or not scenario_text.strip():
                    print(f"Could not extract a valid transcript from call {call.get('Call_ID', 'N/A')}. Moving to unprocessed.")
                    unprocessed_calls.append(call)
                    continue

                # 1. Generate EIDO from raw text (transcript)
                payload = {
                    "template_name": "general_incident.json", 
                    "scenario_description": scenario_text
                }
                response = requests.post(f"{EIDO_AGENT_URL}/api/v1/generate_eido_from_template", json=payload)
                response.raise_for_status()
                eido = response.json().get("generated_eido")
                if not eido:
                    raise ValueError("EIDO generation failed, response did not contain 'generated_eido'.")
                print(f"Generated EIDO for call {call.get('Call_ID', 'N/A')}")

                # 2. Ingest EIDO and create an initial incident
                ingest_payload = {
                    "source": "calls_processing_script",
                    "original_eido": eido
                }
                response = requests.post(f"{EIDO_AGENT_URL}/api/v1/ingest", json=ingest_payload)
                response.raise_for_status()
                incident = response.json()
                print(f"Ingested EIDO and created initial incident record: {incident.get('incident_id')}")
                processed_calls.append(call)

            except requests.exceptions.RequestException as e:
                error_content = e.response.text if e.response else str(e)
                print(f"Error processing call {call.get('Call_ID', 'N/A')}: {error_content}")
                unprocessed_calls.append(call)
            except Exception as e:
                print(f"An unexpected error occurred while processing call {call.get('Call_ID', 'N/A')}: {e}")
                unprocessed_calls.append(call)

            # Wait before processing the next call to avoid overwhelming services
            time.sleep(10)

    with open("data/processed_calls.jsonl", "a") as f:
        for call in processed_calls:
            f.write(json.dumps(call) + "\n")

    # Move unprocessed calls to a separate file to avoid reprocessing loops
    with open("data/unprocessed_calls.jsonl", "a") as f:
        for call in unprocessed_calls:
            f.write(json.dumps(call) + "\n")
    
    # Clear the original calls file now that all calls have been attempted
    with open("data/calls.jsonl", "w") as f:
        pass
    print("Processing complete.")


if __name__ == "__main__":
    process_calls()