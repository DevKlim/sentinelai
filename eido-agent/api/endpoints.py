from fastapi import APIRouter, Depends, HTTPException, Body, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
import uuid
import os
from pydantic import BaseModel

from database.session import get_db
from data_models.schemas import (
    IngestRequest, LinkEidoRequest, TagRequest, EidoBulkActionRequest,
    IncidentPublic, IncidentDetailPublic, EidoReportPublic,
    UpdateEidoRequest, UpdateStatsRequest
)
from services import database as db_service
from agent.agent_core import get_eido_agent
from agent.llm_interface import llm_interface
from config.settings import settings
from services.schema_service import schema_service # Import the service instance

router = APIRouter(prefix="/api/v1", tags=["EIDO Agent"])

class RenameRequest(BaseModel):
    name: str

class CreateIncidentRequest(BaseModel):
    name: str

class TemplateCreationRequest(BaseModel):
    event_type: str
    description: str

class EidoGenerationRequest(BaseModel):
    event_type: str
    scenario_description: str

class TemplateSaveRequest(BaseModel):
    filename: str
    content: Dict[str, Any]


# --- Template Management Endpoints ---

@router.get("/templates", response_model=List[str], tags=["Templates"])
async def list_eido_templates():
    """Lists all available EIDO template filenames."""
    return schema_service.list_templates()

@router.get("/templates/{filename}", response_model=Dict[str, Any], tags=["Templates"])
async def get_eido_template(filename: str):
    """Retrieves the content of a specific EIDO template."""
    try:
        return schema_service.get_template(filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/templates", status_code=status.HTTP_201_CREATED, tags=["Templates"])
async def save_eido_template(request: TemplateSaveRequest):
    """Saves a new EIDO template."""
    try:
        schema_service.save_template(request.filename, request.content)
        return {"message": f"Template '{request.filename}' saved successfully."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save template: {e}")

@router.delete("/templates/{filename}", status_code=status.HTTP_204_NO_CONTENT, tags=["Templates"])
async def delete_eido_template(filename: str):
    """Deletes an EIDO template."""
    try:
        schema_service.delete_template(filename)
        return None
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete template: {e}")


@router.post("/templates/generate", response_model=Dict[str, Any], tags=["Templates"])
async def create_eido_template(request: TemplateCreationRequest):
    """Generates a new EIDO template using a natural language description and RAG."""
    try:
        agent = get_eido_agent()
        new_template = agent.create_eido_template(request.event_type, request.description)
        if "error" in new_template:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=new_template.get("raw_response", "LLM failed to generate valid JSON."))
        return {"generated_template": new_template}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate template: {str(e)}")

# --- Schema Endpoints ---

@router.get("/schema/index", response_model=Dict[str, Any], tags=["Schema"])
async def get_schema_index():
    """Serves the pre-built RAG index chunks for the UI."""
    chunks = schema_service.get_rag_chunks()
    if not chunks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schema index is not loaded or is empty.")
    return {"chunks": chunks}

# --- Settings Endpoints ---

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

# --- EIDO Generation and Ingestion ---

@router.post("/generate_eido_from_scenario", response_model=Dict[str, Any], tags=["EIDO Generation"])
async def generate_eido_from_scenario(request: EidoGenerationRequest):
    """
    Generates an EIDO JSON from a text description using a specified event type.
    """
    try:
        agent = get_eido_agent()
        filled_eido = agent.generate_eido_from_scenario(
            event_type=request.event_type,
            scenario_description=request.scenario_description
        )
        return {"generated_eido": filled_eido}
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"LLM Service Unavailable: {str(e)}")
    except Exception as e:
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

        return await db_service._db_eido_to_public_pydantic(db, report_db)

    except Exception as e:
        print(f"Error during EIDO ingestion: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An internal error occurred during ingestion: {str(e)}")

# --- Incident Management ---

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

@router.post("/incidents/{incident_id}/update_stats", response_model=IncidentDetailPublic, tags=["Incidents"])
async def update_incident_stats_via_llm(incident_id: uuid.UUID, request: UpdateStatsRequest, db: AsyncSession = Depends(get_db)):
    """
    Updates an incident by modifying its latest EIDO report using LLM-driven changes.
    """
    latest_report = await db_service.get_latest_report_for_incident(db, str(incident_id))
    if not latest_report or not latest_report.original_eido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Latest report for incident not found or has no EIDO JSON to modify.")

    updates_description = "Please apply the following updates:\n"
    for key, value in request.stats.items():
        updates_description += f"- Update '{key}' to '{value}'.\n"

    try:
        agent = get_eido_agent()
        modified_eido = agent.modify_eido(latest_report.original_eido, updates_description)

        if "error" in modified_eido:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=modified_eido.get("raw_response", "LLM failed to generate valid updated JSON."))
        
        await db_service.update_eido_report(db, latest_report.eido_id, modified_eido)
        
        updated_incident = await db_service.get_incident_details(db, str(incident_id))
        if not updated_incident:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found after update.")
        return updated_incident

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update incident stats: {str(e)}")

# --- EIDO Report Management ---

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

@router.put("/eidos/{eido_id}", response_model=EidoReportPublic, tags=["EIDO Reports"])
async def update_eido(eido_id: uuid.UUID, request: UpdateEidoRequest, db: AsyncSession = Depends(get_db)):
    """Updates the content of a specific EIDO report."""
    updated_report_db = await db_service.update_eido_report(db, str(eido_id), request.original_eido)
    if not updated_report_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EIDO report not found.")
    
    return await db_service._db_eido_to_public_pydantic(db, updated_report_db)