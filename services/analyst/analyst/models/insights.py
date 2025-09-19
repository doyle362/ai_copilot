from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class InsightCreate(BaseModel):
    location_id: Optional[UUID] = None
    zone_id: str
    kind: Optional[str] = None
    window: Optional[str] = None
    metrics_json: Optional[Dict[str, Any]] = None
    narrative_text: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class InsightResponse(BaseModel):
    id: UUID
    location_id: Optional[UUID]
    zone_id: str
    kind: Optional[str]
    window: Optional[str]
    metrics_json: Optional[Dict[str, Any]]
    narrative_text: Optional[str]
    confidence: Optional[float]
    created_at: datetime
    created_by: Optional[UUID]


class InsightListResponse(BaseModel):
    insights: list[InsightResponse]
    total: int
    offset: int
    limit: int