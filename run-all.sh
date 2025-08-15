#!/bin/bash

SERVICE=$1

if [ "$SERVICE" = "web" ]; then
  # Start nginx to serve the landing page and proxy to other services
  nginx -g 'daemon off;' &

  # Start the dashboard service
  python3 -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8080 &

  # Start the python-services
  ./run-services.sh &

  wait

elif [ "$SERVICE" = "python-services" ]; then
  # Start the python-services
  ./run-services.sh

else
  echo "Unknown service: $SERVICE"
  exit 1
fi