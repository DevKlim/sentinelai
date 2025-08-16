# file: Dockerfile
FROM python:3.11-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends dos2unix curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Copy the entrypoint script and ensure it has correct line endings and permissions
COPY entrypoint.sh /usr/local/bin/
RUN dos2unix /usr/local/bin/entrypoint.sh && chmod +x /usr/local/bin/entrypoint.sh

# Create a non-root user for security best practices
RUN addgroup --system app && adduser --system --group app
RUN chown -R app:app /app
USER app

# Expose the ports for the API and UI services
EXPOSE 8001
EXPOSE 8502

# Set the entrypoint script to be executed when the container starts
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Set the default command, which will be passed as the first argument to the entrypoint
CMD ["api"]