# sentinelai/eido-agent/api/endpoints.py
from fastapi import APIRouter, Depends, HTTPException, Body, Query, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
import uuid
import os
from pydantic import BaseModel

from database.session import get_db
from data_models.schemas import (
    EidoGenerationRequest, IngestRequest, LinkEidoRequest, TagRequest, EidoBulkActionRequest,
    IncidentPublic, IncidentDetailPublic, EidoReportPublic
)
from services import database as db_service
from services import eido_retriever
from agent.agent_core import get_eido_agent
from agent.llm_interface import llm_interface
from config.settings import settings

router = APIRouter(prefix="/api/v1", tags=["EIDO Agent"])

class RenameRequest(BaseModel):
    name: str

class CreateIncidentRequest(BaseModel):
    name: str

# New Pydantic models for template endpoints
class TemplateCreationRequest(BaseModel):
    description: str

class TemplateSaveRequest(BaseModel):
    filename: str
    content: Dict[str, Any]

# Template Management Endpoints (moved from templates_router)
@router.get("/templates", response_model=List[str], tags=["Templates"])
async def get_template_list():
    """Lists all available EIDO template files."""
    return eido_retriever.list_templates()

@router.get("/templates/{filename}", response_model=Dict[str, Any], tags=["Templates"])
async def get_single_template(filename: str):
    """Retrieves the content of a single EIDO template file."""
    template_content = eido_retriever.get_template(filename)
    if template_content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")
    return template_content

@router.delete("/templates/{filename}", status_code=status.HTTP_204_NO_CONTENT, tags=["Templates"])
async def delete_single_template(filename: str):
    """Deletes a single EIDO template file."""
    try:
        success = eido_retriever.delete_template(filename)
        if not success:
            # This case covers file not found or other OS errors
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Template '{filename}' not found or could not be deleted.")
    except ValueError as e:
        # This catches the specific error for the protected template
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.post("/templates", status_code=status.HTTP_201_CREATED, tags=["Templates"])
async def save_new_template(request: TemplateSaveRequest):
    """Saves a new EIDO template file."""
    try:
        success = eido_retriever.save_template(request.filename, request.content)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save template due to an unexpected error.")
    except ValueError as e:
        # Catch the specific error for protected files or invalid names
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return {"message": f"Template '{request.filename}' saved successfully."}

@router.post("/templates/generate", response_model=Dict[str, Any], tags=["Templates"])
async def generate_new_template_from_description(request: TemplateCreationRequest):
    """Generates a new EIDO template using a natural language description and RAG."""
    try:
        agent = get_eido_agent()
        new_template = await agent.create_eido_template(request.description)
        if "error" in new_template:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=new_template.get("raw_response", "LLM failed to generate valid JSON."))
        return {"generated_template": new_template}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate template: {str(e)}")

# New endpoint for Schema Index
@router.get("/schema/index", response_model=Dict[str, Any], tags=["Schema"])
async def get_schema_index():
    """Serves the pre-built RAG index file for the UI."""
    index_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'eido_schema_index.json')
    if not os.path.exists(index_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schema index file not found. Ensure the build process ran correctly.")
    # FastAPI's FileResponse handles the content type automatically for JSON files
    return FileResponse(index_path, media_type="application/json")


@router.get("/settings/env", response_model=dict, tags=["Settings"])
async def get_eido_env_settings():
    """Gets current environment settings for the EIDO agent from the live config."""
    settings_keys_map = {
        "EIDO_LLM_PROVIDER": "llm_provider",
        "EIDO_GOOGLE_API_KEY": "google_api_key",
        "EIDO_OPENAI_API_KEY": "openai_api_key",
        "EIDO_OPENROUTER_API_KEY": "openrouter_api_key",
        "EIDO_GOOGLE_MODEL_NAME": "google_model_name",
        "EIDO_OPENAI_MODEL_NAME": "openai_model_name",
        "EIDO_LOCAL_LLM_URL": "local_llm_url",
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

@router.post("/settings/env", tags=["Settings"])
async def update_env_settings(payload: dict = Body(...)):
    """
    Update settings directly on the Pydantic settings object in memory and
    re-initialize the LLM client to apply the changes immediately.
    """
    new_settings = payload.get("settings", payload)
    if not isinstance(new_settings, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid settings format.")

    try:
        key_map = {
            "EIDO_LLM_PROVIDER": "llm_provider",
            "EIDO_GOOGLE_API_KEY": "google_api_key",
            "EIDO_OPENAI_API_KEY": "openai_api_key",
            "EIDO_OPENROUTER_API_KEY": "openrouter_api_key",
            "EIDO_GOOGLE_MODEL_NAME": "google_model_name",
            "EIDO_OPENAI_MODEL_NAME": "openai_model_name",
            "EIDO_OPENROUTER_MODEL_NAME": "openai_model_name",
            "EIDO_LOCAL_LLM_URL": "local_llm_url",
        }

        for key, value in new_settings.items():
            if value is None or value == "********":
                continue

            attr_name = key_map.get(key.upper())
            if attr_name and hasattr(settings, attr_name):
                print(f"EIDO Agent: Updating setting in memory: {attr_name}")
                setattr(settings, attr_name, str(value))
            else:
                 print(f"EIDO Agent Warning: Setting for key '{key}' not found or not mapped.")
        
        llm_interface.reload()
        
        return {"message": "EIDO Agent settings updated successfully. LLM client re-initialized."}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update EIDO Agent settings: {e}")


@router.post("/generate_eido_from_template", response_model=Dict[str, Any], tags=["EIDO Generation"])
async def generate_eido_from_template(request: EidoGenerationRequest):
    """
    Generates an EIDO JSON from a text description using a specified template,
    enhanced with RAG context from the EIDO schema.
    """
    try:
        # Delegate the entire generation logic to the EidoAgent
        agent = get_eido_agent()
        filled_eido = await agent.generate_eido_from_template_and_scenario(
            template_name=request.template_name,
            scenario_description=request.scenario_description
        )
        return {"generated_eido": filled_eido}
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        # This can be triggered if the LLM client fails to initialize
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"LLM Service Unavailable: {str(e)}")
    except Exception as e:
        # Catch-all for other unexpected errors during generation
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate EIDO: {str(e)}")


@router.post("/ingest", response_model=EidoReportPublic, tags=["Ingestion"])
async def ingest_eido(request: IngestRequest, db: AsyncSession = Depends(get_db)):
    """
    Ingests a raw EIDO JSON, creates an 'uncategorized' EIDO report.
    This report will be processed by the IDX agent for categorization.
    """
    try:
        report_db = await db_service.create_eido_report(
            db=db,
            eido_data=request.original_eido,
            source=request.source,
            incident_id=None
        )
        if not report_db:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create EIDO report record in the database.")

        return EidoReportPublic(
            id=report_db.eido_id,
            timestamp=report_db.timestamp,
            source=report_db.source,
            description=report_db.description,
            original_eido=report_db.original_eido,
            location=report_db.location,
            status=report_db.status,
            incidents=[]
        )
    except Exception as e:
        print(f"Error during EIDO ingestion: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An internal error occurred during ingestion: {str(e)}")

@router.get("/incidents", response_model=List[IncidentPublic], tags=["Incidents"])
async def get_all_incidents(
    status: Optional[str] = None, 
    db: AsyncSession = Depends(get_db)
):
    incidents = await db_service.get_all_incidents(db, status=status)
    return incidents

@router.get("/incidents/{incident_id}", response_model=IncidentDetailPublic, tags=["Incidents"])
async def get_incident_details(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    incident = await db_service.get_incident_details(db, str(incident_id))
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident
    
@router.post("/incidents/create", response_model=IncidentPublic, tags=["Incidents"])
async def create_empty_incident(request: CreateIncidentRequest, db: AsyncSession = Depends(get_db)):
    try:
        new_incident = await db_service.create_empty_incident(db, name=request.name)
        public_incidents = await db_service.get_all_incidents(db)
        for p_inc in public_incidents:
            if p_inc.incident_id == new_incident.incident_id:
                return p_inc
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident created but could not be found.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create incident: {e}")

@router.delete("/incidents/{incident_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Incidents"])
async def delete_incident(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    success = await db_service.delete_incident(db, str(incident_id))
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found or could not be deleted.")
    return None

@router.post("/incidents/{incident_id}/tags", response_model=IncidentPublic, tags=["Incidents"])
async def add_tag_to_incident(incident_id: uuid.UUID, request: TagRequest, db: AsyncSession = Depends(get_db)):
    incident = await db_service.add_tag_to_incident(db, str(incident_id), request.tag)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    public_incidents = await db_service.get_all_incidents(db)
    for p_inc in public_incidents:
        if p_inc.incident_id == str(incident_id):
            return p_inc
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found after tagging.")


@router.post("/incidents/{incident_id}/close", response_model=IncidentPublic, tags=["Incidents"])
async def close_incident(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    incident = await db_service.update_incident_status(db, str(incident_id), "closed")
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    public_incidents = await db_service.get_all_incidents(db)
    for p_inc in public_incidents:
        if p_inc.incident_id == str(incident_id):
            return p_inc
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found after closing.")


@router.post("/incidents/link_eido", response_model=Dict[str, Any], tags=["Incidents"])
async def link_eido_to_incident_endpoint(request: LinkEidoRequest, db: AsyncSession = Depends(get_db)):
    incident_id = await db_service.link_eido_to_incident(db, request.eido_id, request.incident_id, request.incident_details)
    if not incident_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EIDO report not found or linking failed.")
    return {"message": "EIDO linked successfully", "incident_id": incident_id}

@router.post("/incidents/{incident_id}/rename", response_model=IncidentPublic, tags=["Incidents"])
async def rename_incident_endpoint(incident_id: uuid.UUID, request: RenameRequest, db: AsyncSession = Depends(get_db)):
    incident = await db_service.rename_incident(db, str(incident_id), request.name)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    
    public_incidents = await db_service.get_all_incidents(db)
    for p_inc in public_incidents:
        if p_inc.incident_id == str(incident_id):
            return p_inc
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found after renaming.")

@router.get("/eidos", response_model=List[EidoReportPublic], tags=["EIDO Reports"])
async def get_all_eidos(
    status: Optional[str] = Query(None, description="Filter EIDOs by status (e.g., 'uncategorized')"),
    db: AsyncSession = Depends(get_db)
):
    eidos = await db_service.get_eidos_by_status(db, status=status)
    return eidos
    
@router.post("/eidos/bulk-actions", response_model=Dict[str, Any], tags=["EIDO Reports"])
async def perform_eido_bulk_action(request: EidoBulkActionRequest, db: AsyncSession = Depends(get_db)):
    if request.action_type == "delete":
        deleted_count = await db_service.bulk_delete_eidos(db, request.eido_ids)
        return {"message": f"Successfully deleted {deleted_count} EIDO(s)."}
    elif request.action_type == "recategorize":
        if not request.target_incident_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_incident_id is required for recategorize action.")
        updated_count = await db_service.bulk_recategorize_eidos(db, request.eido_ids, request.target_incident_id)
        return {"message": f"Successfully recategorized {updated_count} EIDO(s)."}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Action '{request.action_type}' is not supported.")

@router.delete("/eidos/{eido_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["EIDO Reports"])
async def delete_single_eido(eido_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    success = await db_service.delete_eido_report(db, str(eido_id))
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EIDO report not found or could not be deleted.")
    return None