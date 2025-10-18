#!/bin/bash

# This trap will execute on SIGINT or SIGTERM, cleaning up child processes
trap "echo '--- Shutting down services ---'; pkill -P $$" SIGINT SIGTERM

echo "--- Starting EIDO Agent API on port 8000 ---"
# Use --app-dir to set the Python path correctly for this service
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --app-dir eido-agent &

echo "--- Starting IDX Agent API on port 8001 ---"
# Use --app-dir to set the Python path correctly for this service
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8001 --app-dir idx-agent &

echo "--- Starting Geocoding Agent API on port 8002 ---"
# Use --app-dir to set the Python path correctly for this service
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8002 --app-dir geocoding-agent &


# Wait for all background processes to complete. The script will hang here
# until it's terminated, at which point the trap will run.
echo "All Python services are running. Press Ctrl+C to stop."
wait
