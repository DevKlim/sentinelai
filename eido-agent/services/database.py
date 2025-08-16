import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, and_
from typing import List, Optional, Dict, Any

from data_models import models, schemas

# --- Helper Functions ---

def _extract_info_from_eido(eido_data: Dict[str, Any]):
    """Extracts key information from an EIDO dictionary for incident creation."""
    incident_info = eido_data.get("incidentComponent", {})
    name = incident_info.get("incidentTypeInternalText", "Unnamed Incident")
    inc_type = incident_info.get("incidentTypeCommonRegistryText", "Unknown")
    
    notes = eido_data.get("notesComponent", [])
    summary = notes[0].get("notesActionComments", "No summary available.") if notes else "No summary available."
    
    location_component = eido_data.get("locationComponent", [])
    location_json = None
    locations_coords = []
    if location_component:
        # A real implementation would parse complex PIDF-LO XML. This is a simplified placeholder.
        loc_val = location_component[0].get("locationByValue")
        if isinstance(loc_val, dict) and "latitude" in loc_val and "longitude" in loc_val:
            location_json = {"latitude": loc_val["latitude"], "longitude": loc_val["longitude"]}
            locations_coords.append([loc_val["latitude"], loc_val["longitude"]])
            
    return name, inc_type, summary, location_json, locations_coords


async def _db_eido_to_public_pydantic(db: AsyncSession, eido_report: models.EidoReport) -> schemas.EidoReportPublic:
    """Converts a DB EidoReport model to its public Pydantic schema."""
    incidents_info = []
    if eido_report.incident_id_fk:
        incident = await get_incident_by_incident_id(db, eido_report.incident_id_fk)
        if incident:
            incidents_info.append({"incident_id": incident.incident_id, "name": incident.name})

    return schemas.EidoReportPublic(
        id=eido_report.eido_id,
        timestamp=eido_report.timestamp,
        source=eido_report.source,
        description=eido_report.description,
        original_eido=eido_report.original_eido,
        location=eido_report.location,
        status=eido_report.status,
        incidents=incidents_info
    )

async def _db_incident_to_detailed_pydantic(db: AsyncSession, incident: models.Incident) -> schemas.IncidentDetailPublic:
    """Converts a DB Incident model to its detailed public Pydantic schema."""
    query = select(models.EidoReport).where(models.EidoReport.incident_id_fk == incident.incident_id)
    result = await db.execute(query)
    eido_reports = result.scalars().all()
    
    pydantic_reports = [_ for _ in [await _db_eido_to_public_pydantic(db, r) for r in eido_reports]]

    return schemas.IncidentDetailPublic(
        incident_id=incident.incident_id,
        name=incident.name,
        status=incident.status,
        incident_type=incident.incident_type,
        summary=incident.summary,
        created_at=incident.created_at,
        reports=pydantic_reports,
        tags=incident.tags if incident.tags else [],
        locations=incident.locations if incident.locations else [],
        report_count=len(pydantic_reports)
    )

# --- EIDO Report Functions ---

async def create_eido_report(db: AsyncSession, eido_data: Dict[str, Any], source: str, incident_id: Optional[str] = None) -> models.EidoReport:
    """Creates and saves a new EIDO report."""
    _, _, desc, location_json, _ = _extract_info_from_eido(eido_data)
    
    new_report = models.EidoReport(
        eido_id=str(uuid.uuid4()),
        incident_id_fk=incident_id,
        source=source,
        description=desc,
        location=location_json,
        status="linked" if incident_id else "uncategorized",
        original_eido=eido_data
    )
    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)
    return new_report

async def get_eidos_by_status(db: AsyncSession, status: Optional[str]) -> List[schemas.EidoReportPublic]:
    """Retrieves EIDO reports, optionally filtered by status."""
    query = select(models.EidoReport).order_by(models.EidoReport.timestamp.desc())
    if status:
        query = query.where(models.EidoReport.status == status)
    result = await db.execute(query)
    db_eidos = result.scalars().all()
    return [await _db_eido_to_public_pydantic(db, eido) for eido in db_eidos]

async def delete_eido_report(db: AsyncSession, eido_id: str) -> bool:
    """Deletes a single EIDO report by its UUID."""
    stmt = delete(models.EidoReport).where(models.EidoReport.eido_id == eido_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0

async def bulk_delete_eidos(db: AsyncSession, eido_ids: List[str]) -> int:
    """Deletes multiple EIDO reports."""
    stmt = delete(models.EidoReport).where(models.EidoReport.eido_id.in_(eido_ids))
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount

# --- Incident Functions ---

async def create_incident_from_eido(db: AsyncSession, eido_data: Dict[str, Any]) -> models.Incident:
    """Creates a new incident from EIDO data."""
    name, inc_type, summary, _, locations_coords = _extract_info_from_eido(eido_data)
    
    new_incident = models.Incident(
        incident_id=str(uuid.uuid4()),
        name=name,
        incident_type=inc_type,
        summary=summary,
        status="open",
        locations=locations_coords,
        tags=[]
    )
    db.add(new_incident)
    await db.commit()
    await db.refresh(new_incident)
    return new_incident

async def get_all_incidents(db: AsyncSession, status: Optional[str] = None) -> List[schemas.IncidentPublic]:
    """Retrieves all incidents, optionally filtered by status."""
    query = select(models.Incident).order_by(models.Incident.updated_at.desc())
    if status:
        query = query.where(models.Incident.status == status)
    result = await db.execute(query)
    incidents = result.scalars().all()

    # Create a list of public-facing incident schemas
    public_incidents = []
    for inc in incidents:
        # Get report count efficiently
        count_query = select(models.EidoReport).where(models.EidoReport.incident_id_fk == inc.incident_id)
        count_result = await db.execute(count_query)
        report_count = len(count_result.scalars().all())

        public_incidents.append(schemas.IncidentPublic(
            incident_id=inc.incident_id,
            name=inc.name, status=inc.status, incident_type=inc.incident_type, summary=inc.summary,
            created_at=inc.created_at, tags=inc.tags or [], locations=inc.locations or [],
            report_count=report_count
        ))
    return public_incidents

async def get_incident_details(db: AsyncSession, incident_id: str) -> Optional[schemas.IncidentDetailPublic]:
    """Gets detailed information for a single incident."""
    incident = await get_incident_by_incident_id(db, incident_id)
    if not incident:
        return None
    return await _db_incident_to_detailed_pydantic(db, incident)

async def get_incident_by_incident_id(db: AsyncSession, incident_id: str) -> Optional[models.Incident]:
    """Helper to fetch a single incident DB model by its UUID."""
    result = await db.execute(select(models.Incident).where(models.Incident.incident_id == incident_id))
    return result.scalars().first()

async def delete_incident(db: AsyncSession, incident_id: str) -> bool:
    """Deletes an incident and its associated EIDO reports."""
    await db.execute(delete(models.EidoReport).where(models.EidoReport.incident_id_fk == incident_id))
    result = await db.execute(delete(models.Incident).where(models.Incident.incident_id == incident_id))
    await db.commit()
    return result.rowcount > 0

async def add_tag_to_incident(db: AsyncSession, incident_id: str, tag: str) -> Optional[models.Incident]:
    """Adds a tag to an incident."""
    incident = await get_incident_by_incident_id(db, incident_id)
    if incident:
        current_tags = incident.tags or []
        if tag not in current_tags:
            incident.tags = current_tags + [tag]
            await db.commit()
            await db.refresh(incident)
    return incident

async def update_incident_status(db: AsyncSession, incident_id: str, new_status: str) -> Optional[models.Incident]:
    """Updates the status of an incident."""
    incident = await get_incident_by_incident_id(db, incident_id)
    if incident:
        incident.status = new_status
        await db.commit()
        await db.refresh(incident)
    return incident

async def link_eido_to_incident(db: AsyncSession, eido_id: str, incident_id: Optional[str], incident_details: Optional[schemas.IncidentCreateDetails]) -> Optional[str]:
    """Links an EIDO to an existing incident or creates a new one."""
    eido_report_res = await db.execute(select(models.EidoReport).where(models.EidoReport.eido_id == eido_id))
    eido_report = eido_report_res.scalars().first()
    if not eido_report:
        return None

    target_incident_id = incident_id
    if not target_incident_id:
        if not incident_details: return None
        new_incident = models.Incident(
            incident_id=str(uuid.uuid4()),
            name=incident_details.incident_name,
            incident_type=incident_details.incident_type,
            summary=incident_details.summary,
            tags=incident_details.tags,
            status="open"
        )
        db.add(new_incident)
        await db.commit()
        await db.refresh(new_incident)
        target_incident_id = new_incident.incident_id
    
    eido_report.incident_id_fk = target_incident_id
    eido_report.status = "linked"
    await db.commit()
    return target_incident_id