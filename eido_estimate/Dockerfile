# sentinelai/eido_estimate/Dockerfile
# This Dockerfile creates a self-contained environment for running the ML experiment.
FROM python:3.9-slim

WORKDIR /app

# Copy the requirements file and install dependencies first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the experiment files
COPY . .

# Expose the default Jupyter port
EXPOSE 8888

# The command to run when the container starts.
# This launches a Jupyter Lab server that can be accessed from the host machine.
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]