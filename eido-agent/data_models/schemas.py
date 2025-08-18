from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Schemas for EIDO Management ---

class EidoBase(BaseModel):
    source: str
    description: Optional[str] = None
    original_eido: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, Any]] = None

class Eido(EidoBase):
    id: str
    timestamp: datetime
    status: str

    class Config:
        from_attributes = True

class IngestRequest(BaseModel):
    source: str
    original_eido: Dict[str, Any]

class EidoGenerationRequest(BaseModel):
    template_name: str
    scenario_description: str


# --- Schemas for Incident Management ---

class EidoReport(BaseModel):
    """Internal representation of an EIDO report linked to an incident."""
    id: str
    timestamp: datetime
    source: str
    description: Optional[str] = None
    original_eido: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class EidoReportPublic(BaseModel):
    """Public-facing schema for an EIDO report, used within IncidentDetailPublic."""
    id: str
    timestamp: datetime
    source: str
    description: Optional[str] = None
    original_eido: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, Any]] = None
    status: str  # <-- FIX: Added missing status field
    incidents: Optional[List[Dict[str, Any]]] = []

    class Config:
        from_attributes = True

class Incident(BaseModel):
    """Internal representation of an incident, including full reports."""
    incident_id: str
    name: str
    status: str
    incident_type: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime
    reports: List[EidoReport] = []
    tags: List[str] = []
    locations: List[List[float]] = []
    report_count: int = 0

    class Config:
        from_attributes = True

class IncidentPublic(BaseModel):
    """A public-facing schema for incidents, suitable for list views."""
    incident_id: str
    name: str
    status: str
    incident_type: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime
    tags: List[str] = []
    locations: List[List[float]] = []
    report_count: int = 0

    class Config:
        from_attributes = True

class IncidentDetailPublic(BaseModel):
    """Public-facing schema for a single incident's detailed view."""
    incident_id: str
    name: str
    status: str
    incident_type: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime
    reports: List[EidoReportPublic] = []
    tags: List[str] = []
    locations: List[List[float]] = []
    report_count: int = 0

    class Config:
        from_attributes = True

class IncidentCreateDetails(BaseModel):
    incident_name: str
    incident_type: str
    summary: str
    tags: List[str]

class LinkEidoRequest(BaseModel):
    eido_id: str
    incident_id: Optional[str] = None
    incident_details: Optional[IncidentCreateDetails] = None


# --- Schema for Tagging ---

class TagRequest(BaseModel):
    tag: str

# --- Schemas for Bulk Actions ---
class EidoBulkActionRequest(BaseModel):
    action: str
    eido_ids: List[str]
    target_incident_id: Optional[str] = None

# --- FIX for ImportError ---
# Alias EidoReport to ReportCoreData to satisfy imports in other modules
ReportCoreData = EidoReport