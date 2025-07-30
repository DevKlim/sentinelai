
from fastapi import APIRouter, HTTPException, Body, UploadFile, File
from fastapi.openapi.utils import get_openapi
import httpx
import json

from models.schemas import Incident, CorrelationRequest, CorrelationResponse
from config.settings import settings

router = APIRouter(prefix="/api/v1", tags=["Incidents", "EIDO"])

EIDO_AGENT_URL = settings.eido_agent_url

# Store "claimed" incidents in memory for simplicity
claimed_incidents = set()

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

@router.post("/incidents/{incident_id}/correlate", response_model=list[Incident])
async def correlate_incident_endpoint(incident_id: str):
    """
    Correlate an incident with existing incidents based on semantic similarity.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Get all incidents from the EIDO agent
            response = await client.get(f"{EIDO_AGENT_URL}/api/v1/incidents")
            response.raise_for_status()
            incidents = response.json()

            # Find the target incident
            target_incident = next((inc for inc in incidents if inc['incident_id'] == incident_id), None)
            if not target_incident:
                raise HTTPException(status_code=404, detail="Target incident not found")

            # Generate embeddings for all incident names
            for inc in incidents:
                if inc['incident_id'] not in incident_embeddings:
                    incident_embeddings[inc['incident_id']] = model.encode(inc['name'])

            target_embedding = incident_embeddings[incident_id]

            # Calculate similarities and find correlated incidents
            correlated_incidents = []
            for inc in incidents:
                if inc['incident_id'] != incident_id:
                    similarity = util.cos_sim(target_embedding, incident_embeddings[inc['incident_id']])
                    if similarity > 0.8: # Similarity threshold
                        correlated_incidents.append(inc)
            
            return correlated_incidents

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to EIDO Agent: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during correlation: {e}")

