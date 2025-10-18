# sentinelai/dashboard/Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Copy the requirements file first to leverage Docker's layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into a 'dashboard' subdirectory.
# This makes 'dashboard' a runnable package.
COPY . ./dashboard/

# This command is run from the WORKDIR (/app) and executes 'dashboard' as a module,
# which correctly resolves the relative imports (e.g., `from . import auth`).
CMD ["python", "-m", "uvicorn", "dashboard.main:app", "--host", "0.0.0.0", "--port", "8080"]