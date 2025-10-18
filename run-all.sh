#!/bin/bash
set -e

SERVICE=$1

if [ "$SERVICE" = "web" ]; then
  # Start the python-services script in the background. It will launch all Python APIs.
  echo "Starting Python services in the background..."
  /app/run-services.sh &

  # Start the dashboard service, providing the correct internal URLs.
  # In this single-container setup, all services are on localhost.
  echo "Starting dashboard service on port 8080..."
  export EIDO_API_URL="http://localhost:8000"
  export IDX_API_URL="http://localhost:8001"
  export GEOCODING_API_URL="http://localhost:8002"
  # FIX: Run as a module from the root directory to resolve relative imports correctly.
  (python3 -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8080) &

  # Wait a few seconds to let backend services initialize before starting nginx
  echo "Waiting for services to initialize..."
  sleep 5

  # Start nginx in the foreground. It serves as the main entrypoint.
  echo "Starting NGINX..."
  nginx -g 'daemon off;'

else
  echo "Unknown service: $SERVICE"
  exit 1
fi