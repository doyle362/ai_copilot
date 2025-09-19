from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class ThreadCreate(BaseModel):
    insight_id: Optional[UUID] = None
    zone_id: Optional[str] = None
    thread_type: str = 'insight'


class ThreadResponse(BaseModel):
    id: int
    insight_id: Optional[UUID] = None
    zone_id: Optional[str] = None
    thread_type: str = 'insight'
    status: str
    created_at: datetime


class MessageCreate(BaseModel):
    content: str
    role: str = Field(..., pattern=r"^(user|ai|system)$")
    meta: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    id: int
    thread_id: int
    role: str
    content: str
    meta: Optional[Dict[str, Any]]
    created_by: Optional[UUID]
    created_at: datetime


class ThreadWithMessagesResponse(BaseModel):
    thread: ThreadResponse
    messages: List[MessageResponse]