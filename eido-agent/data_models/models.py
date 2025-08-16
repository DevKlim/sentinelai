import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base

# The Base for all our models
Base = declarative_base()

class Incident(Base):
    __tablename__ = "incidents"
    
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    incident_type = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    status = Column(String, default="open", nullable=False)
    locations = Column(JSON, nullable=True) # Storing as [[lat, lon], ...]
    tags = Column(JSON, nullable=True) # Storing as a list of strings
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class EidoReport(Base):
    __tablename__ = "eido_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    eido_id = Column(String, unique=True, index=True, nullable=False)
    incident_id_fk = Column(String, index=True, nullable=True) # Can be nullable until categorized
    source = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    description = Column(Text, nullable=True)
    location = Column(JSON, nullable=True)
    status = Column(String, default="uncategorized", nullable=False) # e.g., uncategorized, processed, archived
    original_eido = Column(JSON, nullable=False)