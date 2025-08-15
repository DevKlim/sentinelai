# Stage 1: Build the Next.js application (landing page)
FROM node:18-alpine AS landing-builder
WORKDIR /app
COPY landing/package*.json ./
RUN npm install --legacy-peer-deps
COPY landing/ ./
RUN npm run build

# Stage 2: Build the dashboard application
FROM python:3.9-slim AS dashboard-builder
WORKDIR /app
COPY dashboard/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY dashboard/ ./

# Stage 3: Build the python-services application
FROM python:3.10-slim AS python-services-builder
WORKDIR /app
RUN apt-get update && apt-get install -y tesseract-ocr && rm -rf /var/lib/apt/lists/*
COPY requirements.python-services.txt ./
RUN pip install --no-cache-dir -r requirements.python-services.txt
COPY sentinelai /app/sentinelai
COPY eido-agent /app/eido-agent
COPY idx-agent /app/idx-agent
COPY calls_processing.py /app/
COPY run-services.sh /app/
RUN chmod +x /app/run-services.sh

# Final stage: Production image
FROM python:3.10-slim
WORKDIR /app

# Install nginx and dependencies
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*
COPY requirements.python-services.txt ./
RUN pip install --no-cache-dir -r requirements.python-services.txt

# Copy artifacts from the builders
COPY --from=landing-builder /app/out /usr/share/nginx/html
COPY --from=dashboard-builder /app /app/dashboard
COPY --from=python-services-builder /app /app

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy run script
COPY run-all.sh .
RUN chmod +x run-all.sh

# Expose ports
EXPOSE 80 8080 8000 8001

# Run the script
CMD ["./run-all.sh", "web"]
