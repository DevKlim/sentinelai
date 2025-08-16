# Issues Log

This file tracks issues and their resolutions during the development of the SDSC Orchestrator.

## Issue 1: EIDO Agent Environment Variables

*   **Problem:** The `eido-agent` container was not loading the environment variables from the `.env` file, causing errors related to missing API keys and database URLs.
*   **Error Message:**
    ```
    WARNING:config.settings:LLM_PROVIDER is 'google' but GOOGLE_API_KEY is not set.
    ERROR:config.settings:CRITICAL: DATABASE_URL is not set. The application cannot connect to the database.
    CRITICAL:services.geocoding:Nominatim User-Agent is not configured or uses default/invalid format...
    ValueError: FATAL: DATABASE_URL is not configured...
    ```
*   **Fix:** I updated the `docker-compose.yml` file to explicitly specify the `env_file` for the `eido-agent` service.
*   **Status:** Believed to be fixed. Awaiting user confirmation.

## Issue 2: IDX Agent File Path

*   **Problem:** The `idx-agent` container was unable to find the `app.py` file, causing the Streamlit application to fail.
*   **Error Message:**
    ```
    Error: Invalid value: File does not exist: app.py
    ```
*   **Fix Attempt 1:** I updated the `docker-compose.yml` file to set the `working_dir` for the `idx-agent` service to the `ui` directory and specified the command to run the Streamlit app.
*   **Status:** The issue persists.
*   **Analysis:** The `Dockerfile` for the `idx-agent` has an `ENTRYPOINT` and the `docker-compose.yml` had a `command`. This caused a conflict. The `entrypoint.sh` script also had an incorrect path.
*   **Fix Attempt 2:** I have removed the `command` and `working_dir` from the `docker-compose.yml` for the `idx-agent` service to rely on the `Dockerfile`'s `ENTRYPOINT`.
*   **Status:** The issue persists.
*   **Analysis 2:** The `idx-agent/Dockerfile` was creating an incorrect file structure. The `WORKDIR` was set to `/app/ui` and the code was copied into that directory, resulting in the `app.py` file being at `/app/ui/ui/app.py`.
*   **Fix Attempt 3:** I have modified the `idx-agent/Dockerfile` to set the `WORKDIR` to `/app` and updated the `ENTRYPOINT` to `["streamlit", "run", "ui/app.py"]`.
*   **Status:** Believed to be fixed. Awaiting user confirmation.