import json
import requests
import time
import os
import sys

EIDO_AGENT_URL = os.environ.get("EIDO_AGENT_URL", "http://localhost:8000")
IDX_AGENT_URL = os.environ.get("IDX_AGENT_URL", "http://localhost:8001")

def process_calls():
    processed_calls = []
    unprocessed_calls = []

    # Check if the data file exists
    if not os.path.exists("data/calls.jsonl"):
        print("data/calls.jsonl not found. Exiting.")
        return

    with open("data/calls.jsonl", "r") as f:
        for line in f:
            call = json.loads(line)
            print(f"Processing call: {call}")

            try:
                # 1. Generate EIDO from raw text (transcript)
                # The EIDO agent uses an LLM to parse the 'scenario_description' 
                # into a structured EIDO JSON and generate a summary.
                response = requests.post(f"{EIDO_AGENT_URL}/api/v1/generate_eido_from_template", json={"template_name": "general_incident.json", "scenario_description": call["Transcript"]})
                response.raise_for_status()
                eido = response.json().get("generated_eido")
                print(f"Generated EIDO: {eido}")

                # 2. Ingest EIDO and create an initial incident
                # The payload must be wrapped with a source and the original EIDO object.
                ingest_payload = {
                    "source": "calls_processing_script",
                    "original_eido": eido
                }
                response = requests.post(f"{EIDO_AGENT_URL}/api/v1/ingest", json=ingest_payload)
                response.raise_for_status()
                incident = response.json()
                print(f"Ingested EIDO and created initial incident record: {incident}")
                processed_calls.append(call)

                # The IDX agent will later find this 'uncategorized' EIDO
                # and use its LLM to cluster it into a new or existing 'open' incident.

            except requests.exceptions.RequestException as e:
                print(f"Error processing call: {e}")
                unprocessed_calls.append(call)

            # Wait before processing the next call to avoid overwhelming services
            time.sleep(10) 
            
            # The original script had sys.exit(0) here, which would stop it
            # after one call. It has been removed to allow processing all calls.
            # If you want to process only one call for testing, you can add it back.
            # sys.exit(0)


    with open("data/processed_calls.jsonl", "a") as f:
        for call in processed_calls:
            f.write(json.dumps(call) + "\n")

    # Overwrite the original calls file with any that were unprocessed
    with open("data/calls.jsonl", "w") as f:
        for call in unprocessed_calls:
            f.write(json.dumps(call) + "\n")

if __name__ == "__main__":
    process_calls()