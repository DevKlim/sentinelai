from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional, Dict, Any

from models.schemas import IncidentPublic, EidoReportPublic
from services import eido_service
from services.categorizer import categorizer_thread
from services.llm_service import llm_service
from config.settings import settings

router = APIRouter(prefix="/api/v1", tags=["IDX Agent"])

@router.get("/incidents", response_model=List[IncidentPublic])
async def get_all_incidents(
    status: Optional[str] = None
):
    """
    Proxies the request to the EIDO service to get all incidents.
    """
    return await eido_service.get_incidents_from_eido_agent(status=status)

@router.get("/eidos/uncategorized", response_model=List[EidoReportPublic])
async def get_uncategorized_eidos():
    """
    Proxies the request to the EIDO service to get uncategorized EIDOs.
    """
    return await eido_service.get_eidos_from_eido_agent(status="uncategorized")

# --- Settings Endpoints ---

@router.get("/settings/categorizer/status", response_model=Dict[str, Any], tags=["Settings"])
async def get_categorizer_status():
    """Gets the current status of the categorizer background thread."""
    return categorizer_thread.get_status()

@router.post("/settings/categorizer/toggle", response_model=Dict[str, Any], tags=["Settings"])
async def toggle_categorizer(payload: Dict[str, bool] = Body(...)):
    """Enables or disables the categorizer background thread."""
    enable = payload.get('enable')
    if enable is None:
        raise HTTPException(status_code=400, detail="Missing 'enable' boolean in request body.")

    categorizer_thread.set_enabled(enable)
    if enable:
        categorizer_thread.start()
    else:
        categorizer_thread.stop()
    
    return {"message": f"Categorizer has been {'enabled' if enable else 'disabled'}.", "new_state": categorizer_thread.get_status()}

@router.get("/settings/env", response_model=dict, tags=["Settings"])
async def get_idx_env_settings():
    """Gets current environment settings for the IDX agent."""
    settings_keys_map = {
        "IDX_LLM_PROVIDER": "llm_provider",
        "IDX_GOOGLE_API_KEY": "google_api_key",
        "IDX_OPENAI_API_KEY": "openai_api_key",
        "IDX_GOOGLE_MODEL_NAME": "google_model_name",
        "IDX_OPENAI_MODEL_NAME": "openai_model_name",
        "IDX_LOCAL_LLM_URL": "local_llm_url",
    }
    current_settings = {}
    for env_key, attr_name in settings_keys_map.items():
        value = getattr(settings, attr_name, None)
        if "API_KEY" in env_key and value:
            current_settings[env_key] = "********"
        else:
            current_settings[env_key] = value or ""
    return current_settings

@router.post("/settings/env", tags=["Settings"])
async def update_env_settings(payload: dict = Body(...)):
    """Updates settings for the IDX agent and re-initializes its LLM client."""
    new_settings = payload.get("settings", {})
    
    key_map = {
        "IDX_LLM_PROVIDER": "llm_provider",
        "IDX_GOOGLE_API_KEY": "google_api_key",
        "IDX_OPENAI_API_KEY": "openai_api_key",
        "IDX_GOOGLE_MODEL_NAME": "google_model_name",
        "IDX_OPENAI_MODEL_NAME": "openai_model_name",
        "IDX_LOCAL_LLM_URL": "local_llm_url",
    }
    
    try:
        for key, value in new_settings.items():
            attr_name = key_map.get(key.upper())
            if attr_name and hasattr(settings, attr_name) and value != "********":
                setattr(settings, attr_name, value)
        
        llm_service.reload()
        # After reloading, we might need to restart the categorizer if it was off due to bad config
        categorizer_thread.start_if_enabled()

        return {"message": "IDX Agent settings updated successfully. LLM client re-initialized."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update IDX Agent settings: {e}")
