from fastapi import APIRouter, HTTPException, Body, UploadFile, File
from fastapi.openapi.utils import get_openapi
import httpx
import json
from dotenv import set_key, get_key, find_dotenv
import os

from models.schemas import Incident, CorrelationRequest, CorrelationResponse
from config.settings import settings

router = APIRouter(prefix="/api/v1", tags=["Incidents", "EIDO", "Settings"])

EIDO_AGENT_URL = settings.eido_agent_url

# Store "claimed" incidents in memory for simplicity
claimed_incidents = set()

@router.get("/settings/env", response_model=dict)
async def get_idx_env_settings():
    """Gets current environment settings for the IDX agent."""
    env_path = find_dotenv()
    if not env_path:
        return {"error": ".env file not found."}
    
    settings_keys = [
        "LLM_PROVIDER", "GOOGLE_API_KEY", "OPENAI_API_KEY",
        "GOOGLE_MODEL_NAME", "OPENAI_MODEL_NAME", "LOCAL_LLM_URL"
    ]
    
    current_settings = {}
    for key in settings_keys:
        value = get_key(env_path, key)
        if "API_KEY" in key and value:
            current_settings[key] = "********"
        else:
            current_settings[key] = value or ""
            
    return current_settings

@router.post("/settings/env")
async def update_env_settings(new_settings: dict):
    """
    Update the .env file with new settings and signal the categorizer to restart.
    """
    try:
        env_path = find_dotenv()
        if not env_path:
             raise HTTPException(status_code=500, detail=".env file not found.")

        for key, value in new_settings.items():
            if value == "********": continue # Don't update masked values
            set_key(env_path, key, str(value))
        
        # Signal the main process to restart the categorizer to pick up new settings.
        with open("restart_categorizer.flag", "w") as f:
            f.write("restart")
        return {"message": "Settings updated successfully. Categorizer will restart."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {e}")

@router.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    return get_openapi(title="IDX Agent API", version="1.0.0", routes=router.routes)

@router.get("/incidents", response_model=list[Incident])
async def get_incidents():
    """
    Get all incidents from the EIDO Agent.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{EIDO_AGENT_URL}/api/v1/incidents")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to EIDO Agent: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while fetching incidents: {e}")


@router.post("/incidents/{incident_id}/claim")
async def claim_incident(incident_id: str):
    """
    Claim an incident for the IDX Agent.
    """
    claimed_incidents.add(incident_id)
    return {"message": f"Incident {incident_id} claimed."}

@router.get("/incidents/claimed", response_model=list[str])
async def get_claimed_incidents():
    """
    Get all claimed incidents.
    """
    return list(claimed_incidents)

@router.post("/eido/upload", response_model=dict)
async def upload_eido(file: UploadFile = File(...)):
    """
    Upload an EIDO JSON file to the EIDO Agent.
    """
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .json files are accepted.")

    content = await file.read()
    try:
        eido_data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format in uploaded file.")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{EIDO_AGENT_URL}/api/v1/ingest", json=eido_data)
            response.raise_for_status()
            # It's possible the EIDO agent returns a success status but non-JSON body
            return response.json()
    except httpx.HTTPStatusError as e:
        # Re-raise the error from the downstream service with more context
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except httpx.RequestError as e:
        # Network-level error
        raise HTTPException(status_code=502, detail=f"Could not connect to EIDO Agent: {e}")
    except json.JSONDecodeError:
        # The EIDO agent returned a success status but the response body was not valid JSON
        raise HTTPException(status_code=502, detail="Received an invalid response from the EIDO Agent.")
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


from sentence_transformers import SentenceTransformer, util

# Load a pre-trained model for sentence embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')

# In-memory store for incident embeddings
incident_embeddings = {}

@router.post("/incidents/{incident_id}/close")
async def close_incident(incident_id: str):
    """
    Close an incident in the EIDO Agent.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{EIDO_AGENT_URL}/api/v1/incidents/{incident_id}/close")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to EIDO Agent: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while closing the incident: {e}")