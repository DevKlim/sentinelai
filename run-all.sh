#!/bin/bash
set -e

SERVICE=$1

if [ "$SERVICE" = "web" ]; then
  # Start the python-services in the background. They will be available on localhost.
  echo "Starting Python services..."
  /app/run-services.sh &

  # Start the dashboard service, providing the correct internal URLs for the other APIs.
  # These services are running in the same container, so they can communicate via localhost.
  echo "Starting dashboard service..."
  export EIDO_API_URL="http://localhost:8000"
  export IDX_API_URL="http://localhost:8001"
  export GEOCODING_API_URL="http://localhost:8002"
  # The dashboard's own API endpoints will use these variables to talk to the other services.
  python3 -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8080 &

  # Start nginx in the foreground. It will serve the landing page and act as a reverse proxy
  # for all the backend services.
  echo "Starting NGINX..."
  nginx -g 'daemon off;'

elif [ "$SERVICE" = "python-services" ]; then
  # This branch is for potential separate execution, not used by the 'web' process.
  echo "Starting Python services directly..."
  /app/run-services.sh

else
  echo "Unknown service: $SERVICE"
  exit 1
fi
