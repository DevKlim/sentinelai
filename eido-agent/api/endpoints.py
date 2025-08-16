from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
import uuid
from pydantic import BaseModel

from database.session import get_db
from data_models.schemas import (
    EidoGenerationRequest, IngestRequest, LinkEidoRequest, TagRequest, EidoBulkActionRequest,
    IncidentPublic, IncidentDetailPublic, EidoReportPublic
)
from services import database as db_service
from services import eido_retriever
from agent.llm_interface import llm_interface # Import the singleton instance
from config.settings import settings
from dotenv import set_key, get_key, find_dotenv

router = APIRouter(prefix="/api/v1", tags=["EIDO", "Incidents"])

class RenameRequest(BaseModel):
    name: str

class CreateIncidentRequest(BaseModel):
    name: str

@router.get("/settings/env", response_model=dict)
async def get_eido_env_settings():
    """Gets current environment settings for the EIDO agent."""
    env_path = find_dotenv()
    if not env_path:
        return {"error": ".env file not found."}
    
    settings_keys = [
        "LLM_PROVIDER", "GOOGLE_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY",
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
async def update_env_settings(payload: dict = Body(...)):
    """Update the .env file with new settings and re-initialize clients."""
    # Handle nested payload from dashboard proxy
    new_settings = payload.get("settings", payload)
    if not isinstance(new_settings, dict):
        raise HTTPException(status_code=400, detail="Invalid settings format.")

    try:
        env_path = find_dotenv()
        if not env_path:
             raise HTTPException(status_code=500, detail=".env file not found.")

        for key, value in new_settings.items():
            # Don't update with masked value or if value is None
            if value == "********" or value is None: continue 
            set_key(env_path, key, str(value))
        
        settings.reload()
        llm_interface.reload()
        
        return {"message": "Settings updated successfully. LLM client re-initialized."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {e}")


@router.post("/generate_eido_from_template", response_model=Dict[str, Any])
async def generate_eido_from_template(request: EidoGenerationRequest):
    """
    Generates an EIDO JSON from a text description using a specified template.
    """
    try:
        template = eido_retriever.get_template(request.template_name)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{request.template_name}' not found.")
        
        filled_eido = await llm_interface.fill_eido_template(template, request.scenario_description)
        return {"generated_eido": filled_eido}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate EIDO: {str(e)}")

@router.post("/ingest", response_model=EidoReportPublic)
async def ingest_eido(request: IngestRequest, db: AsyncSession = Depends(get_db)):
    """
    Ingests a raw EIDO JSON, creates an 'uncategorized' EIDO report.
    This report will be processed by the IDX agent for categorization.
    """
    try:
        # Create the EIDO report without linking it to an incident.
        # The db_service function will automatically set its status to 'uncategorized'.
        report_db = await db_service.create_eido_report(
            db=db,
            eido_data=request.original_eido,
            source=request.source,
            incident_id=None
        )
        if not report_db:
            raise HTTPException(status_code=500, detail="Failed to create EIDO report record in the database.")

        # Manually construct the Pydantic response model.
        # This avoids needing to add a new function to the database service layer for this single use case.
        return EidoReportPublic(
            id=report_db.eido_id,
            timestamp=report_db.timestamp,
            source=report_db.source,
            description=report_db.description,
            original_eido=report_db.original_eido,
            location=report_db.location,
            status=report_db.status,
            incidents=[] # No incidents are linked at this stage.
        )
    except Exception as e:
        print(f"Error during EIDO ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred during ingestion: {str(e)}")

@router.get("/incidents", response_model=List[IncidentPublic])
async def get_all_incidents(
    status: Optional[str] = None, 
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves all incidents, optionally filtered by status.
    """
    incidents = await db_service.get_all_incidents(db, status=status)
    return incidents

@router.get("/incidents/{incident_id}", response_model=IncidentDetailPublic)
async def get_incident_details(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieves detailed information for a specific incident, including all its EIDO reports.
    """
    incident = await db_service.get_incident_details(db, str(incident_id))
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
    
@router.post("/incidents/create", response_model=IncidentPublic)
async def create_empty_incident(request: CreateIncidentRequest, db: AsyncSession = Depends(get_db)):
    """Creates a new, empty incident from scratch with just a name."""
    try:
        new_incident = await db_service.create_empty_incident(db, name=request.name)
        # We need to convert the DB model to a Pydantic model for the response.
        # We can reuse the logic from get_all_incidents for this.
        public_incidents = await db_service.get_all_incidents(db)
        for p_inc in public_incidents:
            if p_inc.incident_id == new_incident.incident_id:
                return p_inc
        raise HTTPException(status_code=404, detail="Incident created but could not be found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create incident: {e}")

@router.delete("/incidents/{incident_id}", status_code=204)
async def delete_incident(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Deletes an incident and all its associated EIDO reports.
    """
    success = await db_service.delete_incident(db, str(incident_id))
    if not success:
        raise HTTPException(status_code=404, detail="Incident not found or could not be deleted.")
    return None

@router.post("/incidents/{incident_id}/tags", response_model=IncidentPublic)
async def add_tag_to_incident(incident_id: uuid.UUID, request: TagRequest, db: AsyncSession = Depends(get_db)):
    """
    Adds a tag to a specific incident.
    """
    incident = await db_service.add_tag_to_incident(db, str(incident_id), request.tag)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    public_incidents = await db_service.get_all_incidents(db)
    for p_inc in public_incidents:
        if p_inc.incident_id == str(incident_id):
            return p_inc
    raise HTTPException(status_code=404, detail="Incident not found after tagging.")


@router.post("/incidents/{incident_id}/close", response_model=IncidentPublic)
async def close_incident(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Closes an incident.
    """
    incident = await db_service.update_incident_status(db, str(incident_id), "closed")
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")
    public_incidents = await db_service.get_all_incidents(db)
    for p_inc in public_incidents:
        if p_inc.incident_id == str(incident_id):
            return p_inc
    raise HTTPException(status_code=404, detail="Incident not found after closing.")


@router.post("/incidents/link_eido", response_model=Dict[str, Any])
async def link_eido_to_incident_endpoint(request: LinkEidoRequest, db: AsyncSession = Depends(get_db)):
    """
    Links an existing uncategorized EIDO to an existing incident,
    or creates a new incident and links the EIDO to it.
    """
    incident_id = await db_service.link_eido_to_incident(db, request.eido_id, request.incident_id, request.incident_details)
    if not incident_id:
        raise HTTPException(status_code=404, detail="EIDO report not found or linking failed.")
    return {"message": "EIDO linked successfully", "incident_id": incident_id}

@router.post("/incidents/{incident_id}/rename", response_model=IncidentPublic)
async def rename_incident_endpoint(incident_id: uuid.UUID, request: RenameRequest, db: AsyncSession = Depends(get_db)):
    """Renames an incident."""
    incident = await db_service.rename_incident(db, str(incident_id), request.name)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # This pattern is inefficient but consistent with other endpoints in the file.
    public_incidents = await db_service.get_all_incidents(db)
    for p_inc in public_incidents:
        if p_inc.incident_id == str(incident_id):
            return p_inc
    raise HTTPException(status_code=404, detail="Incident not found after renaming.")

@router.get("/eidos", response_model=List[EidoReportPublic])
async def get_all_eidos(
    status: Optional[str] = Query(None, description="Filter EIDOs by status (e.g., 'uncategorized')"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves all EIDO reports, optionally filtered by status.
    """
    eidos = await db_service.get_eidos_by_status(db, status=status)
    return eidos
    
@router.post("/eidos/bulk-actions", response_model=Dict[str, Any])
async def perform_eido_bulk_action(request: EidoBulkActionRequest, db: AsyncSession = Depends(get_db)):
    """
    Performs a bulk action (e.g., delete, recategorize) on a list of EIDOs.
    """
    if request.action_type == "delete":
        deleted_count = await db_service.bulk_delete_eidos(db, request.eido_ids)
        return {"message": f"Successfully deleted {deleted_count} EIDO(s)."}
    elif request.action_type == "recategorize":
        if not request.target_incident_id:
            raise HTTPException(status_code=400, detail="target_incident_id is required for recategorize action.")
        updated_count = await db_service.bulk_recategorize_eidos(db, request.eido_ids, request.target_incident_id)
        return {"message": f"Successfully recategorized {updated_count} EIDO(s)."}
    else:
        raise HTTPException(status_code=400, detail=f"Action '{request.action_type}' is not supported.")

@router.delete("/eidos/{eido_id}", status_code=204)
async def delete_single_eido(eido_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Deletes a single EIDO report.
    """
    success = await db_service.delete_eido_report(db, str(eido_id))
    if not success:
        raise HTTPException(status_code=404, detail="EIDO report not found or could not be deleted.")
    return None