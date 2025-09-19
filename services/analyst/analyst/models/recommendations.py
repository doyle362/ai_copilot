from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class RecommendationCreate(BaseModel):
    location_id: Optional[UUID] = None
    zone_id: str
    type: Optional[str] = None
    proposal: Optional[Dict[str, Any]] = None
    rationale_text: Optional[str] = None
    expected_lift_json: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    requires_approval: bool = True
    thread_id: Optional[int] = None


class RecommendationResponse(BaseModel):
    id: UUID
    location_id: Optional[UUID]
    zone_id: str
    type: Optional[str]
    proposal: Optional[Dict[str, Any]]
    rationale_text: Optional[str]
    expected_lift_json: Optional[Dict[str, Any]]
    confidence: Optional[float]
    requires_approval: bool
    memory_ids_used: List[int]
    prompt_version_id: Optional[int]
    thread_id: Optional[int]
    status: str
    created_at: datetime


class RecommendationListResponse(BaseModel):
    recommendations: list[RecommendationResponse]
    total: int
    offset: int
    limit: int


class RecommendationGenerateRequest(BaseModel):
    zone_id: str
    location_id: Optional[UUID] = None
    context: Optional[str] = None
    force_reason_model: bool = False