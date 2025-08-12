#!/bin/bash
set -e

# Start EIDO Agent in the background
echo "Starting EIDO Agent API on port 8000..."
cd /app/eido-agent
uvicorn api.main:app --host 0.0.0.0 --port 8000 &
EIDO_PID=$!
cd /app

# Start IDX Agent in the background
echo "Starting IDX Agent API on port 8001..."
cd /app/idx-agent
uvicorn api.main:app --host 0.0.0.0 --port 8001 &
IDX_PID=$!

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?