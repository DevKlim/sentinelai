from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class GeocodeRequest(BaseModel):
    text_description: str
    area_context: Optional[str] = None

class AgentStep(BaseModel):
    step_number: int
    step_name: str
    details: str
    status: str  # e.g., "Success", "Failure"
    result: Optional[Dict[str, Any]] = None

class GeocodeResponse(BaseModel):
    latitude: float
    longitude: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    source: str  # e.g., "llm-agent", "area-cache"
    agent_trace: List[AgentStep] = Field(default=[], description="Trace of the agent's steps to reach the conclusion.")

class Area(BaseModel):
    name: str = Field(..., description="Unique name for the area, e.g., 'UC San Diego'.")
    aliases: List[str] = Field(default=[], description="Alternative names, e.g., 'UCSD'.")
    latitude: float
    longitude: float
    radius_meters: float = Field(default=2000, description="Approximate radius of the area in meters.")
    context_clues: List[str] = Field(default=[], description="List of descriptive clues, e.g., 'Geisel Library', 'Price Center', 'Sun God statue'.")
