from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any
from pydantic import BaseModel

from config.settings import settings
from services.llm_service import get_llm_service
from services.categorizer import start_categorizer, stop_categorizer, get_categorizer_status

router = APIRouter(prefix="/api/v1", tags=["Settings", "Categorizer"])

@router.get("/settings/env", response_model=dict)
async def get_idx_env_settings():
    """Gets current environment settings for the IDX agent from the live config."""
    settings_keys_map = {
        "IDX_LLM_PROVIDER": "llm_provider",
        "IDX_GOOGLE_API_KEY": "google_api_key",
        "IDX_OPENAI_API_KEY": "openai_api_key",
        "IDX_OPENROUTER_API_KEY": "openrouter_api_key",
        "IDX_GOOGLE_MODEL_NAME": "google_model_name",
        "IDX_OPENAI_MODEL_NAME": "openai_model_name",
        "IDX_LOCAL_LLM_URL": "local_llm_url",
    }
    current_settings = {}
    for env_key, attr_name in settings_keys_map.items():
        if hasattr(settings, attr_name):
            value = getattr(settings, attr_name)
            if "API_KEY" in env_key and value:
                current_settings[env_key] = "********"
            else:
                current_settings[env_key] = value or ""
    return current_settings

@router.post("/settings/env")
async def update_env_settings(payload: dict = Body(...)):
    """
    Update settings directly on the Pydantic settings object in memory and
    re-initialize the LLM client to apply the changes immediately.
    """
    new_settings = payload.get("settings", payload)
    if not isinstance(new_settings, dict):
        raise HTTPException(status_code=400, detail="Invalid settings format.")

    try:
        # Map from the environment variable names sent by the dashboard
        # to the attribute names in the Pydantic settings class.
        key_map = {
            "IDX_LLM_PROVIDER": "llm_provider",
            "IDX_GOOGLE_API_KEY": "google_api_key",
            "IDX_OPENAI_API_KEY": "openai_api_key",
            "IDX_OPENROUTER_API_KEY": "openrouter_api_key",
            "IDX_GOOGLE_MODEL_NAME": "google_model_name",
            "IDX_OPENAI_MODEL_NAME": "openai_model_name",
            "IDX_OPENROUTER_MODEL_NAME": "openai_model_name", # Map to a valid attribute
            "IDX_LOCAL_LLM_URL": "local_llm_url",
        }

        for key, value in new_settings.items():
            if value is None or value == "********":
                continue

            attr_name = key_map.get(key.upper())
            if attr_name and hasattr(settings, attr_name):
                print(f"IDX Agent: Updating setting in memory: {attr_name}")
                setattr(settings, attr_name, str(value))
            else:
                 print(f"IDX Agent Warning: Setting for key '{key}' not found or not mapped.")
        
        # Reload the LLM service to pick up new settings from the modified object
        get_llm_service().reload()
        
        return {"message": "IDX Agent settings updated successfully. LLM client re-initialized."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update IDX Agent settings: {e}")

@router.get("/settings/categorizer/status", response_model=Dict[str, Any])
async def get_status():
    """Gets the current status of the background categorizer task."""
    return get_categorizer_status()

class ToggleRequest(BaseModel):
    enable: bool

@router.post("/settings/categorizer/toggle", response_model=Dict[str, str])
async def toggle_categorizer_endpoint(request: ToggleRequest):
    """Starts or stops the background categorizer task."""
    if request.enable:
        if not get_llm_service().is_configured():
             raise HTTPException(status_code=400, detail="Cannot enable categorizer: LLM is not configured. Please set the API key first.")
        success = start_categorizer()
        message = "Categorizer started successfully." if success else "Categorizer is already running."
    else:
        success = stop_categorizer()
        message = "Categorizer stopped successfully." if success else "Categorizer is not running."
    return {"message": message}