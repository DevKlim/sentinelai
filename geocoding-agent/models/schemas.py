from pydantic import BaseModel, Field
from typing import List, Optional

class GeocodeRequest(BaseModel):
    text_description: str
    area_context: Optional[str] = None

class GeocodeResponse(BaseModel):
    latitude: float
    longitude: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    source: str # e.g., "llm-geocoded", "area-cache"

class Area(BaseModel):
    name: str = Field(..., description="Unique name for the area, e.g., 'Disneyland Park'.")
    aliases: List[str] = Field(default=[], description="Alternative names, e.g., 'Disney', 'Magic Kingdom'.")
    latitude: float
    longitude: float
    radius_meters: float = Field(default=500, description="Approximate radius of the area in meters.")
    context_clues: List[str] = Field(default=[], description="List of descriptive clues, e.g., 'near the Matterhorn ride', 'red brick building with a clock'.")
