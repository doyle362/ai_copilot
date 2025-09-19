from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None


class PaginationParams(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=1000)


class TimeWindow(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    window_type: str = Field(default="7d")  # 1d, 7d, 30d, custom


class ZoneScope(BaseModel):
    zone_id: str
    location_id: Optional[UUID] = None