from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class PriceChangeCreate(BaseModel):
    location_id: Optional[UUID] = None
    zone_id: str
    prev_price: Optional[float] = None
    new_price: float = Field(..., gt=0)
    change_pct: Optional[float] = None
    policy_version: Optional[str] = None
    recommendation_id: Optional[UUID] = None
    revert_to: Optional[float] = None
    revert_if: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


class PriceChangeResponse(BaseModel):
    id: UUID
    location_id: Optional[UUID]
    zone_id: str
    prev_price: Optional[float]
    new_price: float
    change_pct: Optional[float]
    policy_version: Optional[str]
    recommendation_id: Optional[UUID]
    applied_by: Optional[UUID]
    applied_at: Optional[datetime]
    revert_to: Optional[float]
    revert_if: Optional[Dict[str, Any]]
    expires_at: Optional[datetime]
    status: str
    created_at: datetime


class ApplyChangeRequest(BaseModel):
    change_id: UUID
    force: bool = False


class RevertChangeRequest(BaseModel):
    change_id: UUID
    reason: Optional[str] = None


class ChangeListResponse(BaseModel):
    changes: List[PriceChangeResponse]
    total: int
    offset: int
    limit: int