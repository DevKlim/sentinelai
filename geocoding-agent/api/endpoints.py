from fastapi import APIRouter, HTTPException, status, Body
from typing import List, Dict, Any

from agent.geocoding_core import geocoding_agent
from services.area_store import area_store
from models.schemas import GeocodeRequest, GeocodeResponse, Area
from config.settings import settings
from agent.geocoding_core import GeocodingLLMInterface

router = APIRouter(prefix="/api/v1", tags=["Geocoding"])

@router.post("/geocode", response_model=GeocodeResponse)
async def geocode_text(request: GeocodeRequest):
    """
    Performs context-aware geocoding on a text description.
    """
    result = geocoding_agent.geocode(request.text_description)
    if not result:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get a valid response from the geocoding agent.")
    return result

@router.get("/areas", response_model=List[Area])
async def list_areas():
    """Lists all known geofenced areas."""
    return area_store.get_all_areas()

@router.post("/areas", response_model=Area, status_code=status.HTTP_201_CREATED)
async def create_area(area: Area):
    """Creates a new geofenced area with context clues."""
    try:
        return area_store.save_area(area)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.delete("/areas/{area_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_area(area_name: str):
    """Deletes a known area."""
    if not area_store.delete_area(area_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Area '{area_name}' not found.")
    return

# --- Settings Endpoint ---
@router.get("/settings/env", response_model=dict, tags=["Settings"])
async def get_geocoding_env_settings():
    settings_keys = [
        "GEOCODING_LLM_PROVIDER", "GEOCODING_GOOGLE_API_KEY", "GEOCODING_OPENAI_API_KEY",
        "GEOCODING_OPENROUTER_API_KEY", "GEOCODING_GOOGLE_MODEL_NAME", "GEOCODING_OPENAI_MODEL_NAME"
    ]
    current_settings = {}
    for key in settings_keys:
        value = getattr(settings, key.replace("GEOCODING_", "").lower(), None)
        if "API_KEY" in key and value:
            current_settings[key] = "********"
        else:
            current_settings[key] = value or ""
    return current_settings

@router.post("/settings/env", tags=["Settings"])
async def update_env_settings(payload: dict = Body(...)):
    new_settings = payload.get("settings", {})
    key_map = {
        "GEOCODING_LLM_PROVIDER": "llm_provider",
        "GEOCODING_GOOGLE_API_KEY": "google_api_key",
        "GEOCODING_OPENAI_API_KEY": "openai_api_key",
        "GEOCODING_OPENROUTER_API_KEY": "openrouter_api_key",
        "GEOCODING_GOOGLE_MODEL_NAME": "google_model_name",
        "GEOCODING_OPENAI_MODEL_NAME": "openai_model_name",
    }
    try:
        for key, value in new_settings.items():
            attr_name = key_map.get(key.upper())
            if attr_name and hasattr(settings, attr_name) and value != "********":
                setattr(settings, attr_name, value)
        
        # Re-initialize the agent's LLM interface
        geocoding_agent.llm_interface = GeocodingLLMInterface()
        return {"message": "Geocoding Agent settings updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
