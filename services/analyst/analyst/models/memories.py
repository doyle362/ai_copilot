from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class MemoryCreate(BaseModel):
    scope: str = Field(..., pattern=r"^(global|client|location|zone)$")
    scope_ref: Optional[UUID] = None
    topic: Optional[str] = None
    kind: str = Field(..., pattern=r"^(canonical|context|exception)$")
    content: str
    source_thread_id: Optional[int] = None
    expires_at: Optional[datetime] = None


class MemoryResponse(BaseModel):
    id: int
    scope: str
    scope_ref: Optional[UUID]
    topic: Optional[str]
    kind: str
    content: str
    source_thread_id: Optional[int]
    expires_at: Optional[datetime]
    created_by: Optional[UUID]
    created_at: datetime
    is_active: bool


class MemoryUpsertRequest(BaseModel):
    memories: List[MemoryCreate]