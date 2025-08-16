
from pydantic import BaseModel, Field
from typing import Optional

class Incident(BaseModel):
    id: str
    text: str

class CorrelationRequest(BaseModel):
    text: str

class CorrelationResponse(BaseModel):
    status: str
    correlation_id: Optional[str] = None
