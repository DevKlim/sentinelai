#!/bin/bash

# --- DIAGNOSTIC STEP ---
# Print the critical environment variable to the logs to verify what the app is actually seeing.
echo "--- DIAGNOSTIC: Printing DATABASE_URL from inside the container ---"
echo "DATABASE_URL=${DATABASE_URL}"
echo "------------------------------------------------------------------"

# --- SERVICE DISCOVERY ---
# Export the URLs for the services so they can communicate with each other.
# In this single-container setup, all processes can reach each other on localhost.
export EIDO_AGENT_URL="http://localhost:8000"
export IDX_AGENT_URL="http://localhost:8001"

# This trap will execute on SIGINT or SIGTERM, cleaning up child processes
trap "echo '--- Shutting down services ---'; pkill -P $$" SIGINT SIGTERM

echo "--- Starting EIDO Agent API ---"
# Change directory into the service folder before running uvicorn
(cd /app/eido-agent && uvicorn api.main:app --host 0.0.0.0 --port 8000) &

echo "--- Starting IDX Agent API ---"
# Change directory into the service folder before running uvicorn
(cd /app/idx-agent && uvicorn api.main:app --host 0.0.0.0 --port 8001) &

# Wait for all background processes to complete. The script will hang here
# until it's terminated, at which point the trap will run.
echo "All services are running. Press Ctrl+C to stop."
wait