#!/bin/bash

echo "Starting SentinelAI Emergency Response Platform..."
echo

echo "Building and starting all services..."
docker-compose up --build -d

echo
echo "System is starting up. Please wait for all services to be ready..."
echo
echo "Access points:"
echo "- Landing Page: http://localhost"
echo "- Dashboard: http://localhost/dashboard"
echo "- EIDO Agent UI: http://localhost/eido-ui"
echo "- IDX Agent UI: http://localhost/idx-ui"
echo
echo "To stop the system, run: docker-compose down"
echo "To view logs, run: docker-compose logs -f"
echo