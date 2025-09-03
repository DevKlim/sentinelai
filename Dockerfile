# sentinelai/Dockerfile
# sdsc-orchestrator/Dockerfile
# Stage 1: Build the Next.js application (landing page)
FROM node:18-alpine AS landing-builder
WORKDIR /app
COPY landing/package*.json ./
RUN npm install --legacy-peer-deps
COPY landing/ ./
# The "output: 'export'" in next.config.mjs makes this generate a static site in /app/out
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
# Install system dependencies, ADDING ca-certificates and openssl
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    openssl \
    tesseract-ocr \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*
# Copy requirements and install them to leverage Docker layer caching
COPY requirements.python-services.txt ./
RUN pip install --no-cache-dir -r requirements.python-services.txt
# Copy application code
COPY eido-agent /app/eido-agent
COPY idx-agent /app/idx-agent
COPY calls_processing.py /app/
COPY run-services.sh /app/

# --- FIX: Run the RAG indexer during the build ---
RUN python /app/eido-agent/utils/rag_indexer.py

RUN chmod +x /app/run-services.sh

# Final stage: Production image
FROM python:3.10-slim
WORKDIR /app

# Install dependencies, ADDING ca-certificates and openssl to the final image
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    openssl \
    nginx \
    dos2unix \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.python-services.txt ./
RUN pip install --no-cache-dir -r requirements.python-services.txt

# Copy pre-built static assets and application code from builders
COPY --from=landing-builder /app/out/ /usr/share/nginx/html/
RUN addgroup --system nginx && adduser --system --ingroup nginx nginx
RUN chown -R nginx:nginx /usr/share/nginx/html/
COPY --from=dashboard-builder /app/ /app/dashboard
COPY --from=python-services-builder /app/ /app/

# Copy nginx configuration for Fly.io
RUN rm -f /etc/nginx/conf.d/default.conf /etc/nginx/sites-enabled/default
COPY nginx.fly.conf /etc/nginx/conf.d/default.conf

# Copy run scripts, fix line endings, and make them executable
COPY run-all.sh .
COPY run-services.sh .
RUN dos2unix run-all.sh && chmod +x run-all.sh
RUN dos2unix run-services.sh && chmod +x run-services.sh

# Expose all necessary ports
EXPOSE 80 8080 8000 8001

# The command to run when the container starts.
CMD ["./run-all.sh", "web"]