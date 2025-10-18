
# sentinelai/Dockerfile
# This Dockerfile creates a single, unified image for deployment on platforms like Fly.io.

# Stage 1: Build the Next.js application (landing page)
FROM node:18-alpine AS landing-builder
WORKDIR /app
COPY landing/package*.json ./
RUN npm install --legacy-peer-deps
COPY landing/ ./
# The "output: 'export'" in next.config.mjs generates a static site in /app/out
RUN npm run build

# Stage 2: Build the Python services and dashboard
FROM python:3.10-slim AS python-builder
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for all services in a single command.
# This allows pip's resolver to find a compatible set of packages for all services.
COPY requirements.python-services.txt ./
COPY dashboard/requirements.txt ./dashboard-requirements.txt
RUN pip install --no-cache-dir -r requirements.python-services.txt -r dashboard-requirements.txt

# Copy application code for all Python services
COPY eido-agent /app/eido-agent
COPY idx-agent /app/idx-agent
COPY geocoding-agent /app/geocoding-agent
COPY dashboard /app/dashboard

# --- Run build-time scripts ---
# Pre-process the EIDO schema to create the RAG index
RUN python3 /app/eido-agent/utils/rag_indexer.py


# Final stage: Production image
FROM python:3.10-slim
WORKDIR /app

# Install only necessary runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-installed Python dependencies and app code from the builder stage
COPY --from=python-builder /usr/local/lib/python3.10/site-packages/ /usr/local/lib/python3.10/site-packages/
COPY --from=python-builder /app/ /app/

# Copy pre-built static assets for the landing page
COPY --from=landing-builder /app/out/ /usr/share/nginx/html/

# Configure NGINX
# Remove the default site configuration to avoid conflicts
RUN rm -f /etc/nginx/sites-enabled/default
COPY nginx.fly.conf /etc/nginx/conf.d/default.conf

# Copy run scripts, fix line endings, and make them executable
COPY run-all.sh .
COPY run-services.sh .
RUN dos2unix run-all.sh && chmod +x run-all.sh
RUN dos2unix run-services.sh && chmod +x run-services.sh

# Expose the public-facing port (NGINX)
EXPOSE 80

# The command to run when the container starts.
CMD ["./run-all.sh", "web"]