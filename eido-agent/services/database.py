from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from data_models import models, schemas

async def get_incidents(db: AsyncSession, status: Optional[str] = None) -> List[models.Incident]:
    query = select(models.Incident).order_by(models.Incident.created_at.desc())
    if status:
        query = query.where(models.Incident.status == status)
    result = await db.execute(query)
    return result.scalars().all()

async def get_incident_by_incident_id(db: AsyncSession, incident_id: str) -> Optional[models.Incident]:
    result = await db.execute(
        select(models.Incident).where(models.Incident.incident_id == incident_id)
    )
    return result.scalars().first()