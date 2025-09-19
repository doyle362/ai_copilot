from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class PromptVersionCreate(BaseModel):
    scope: str = Field(..., pattern=r"^(global|client|location|zone)$")
    scope_ref: Optional[UUID] = None
    title: Optional[str] = None
    system_prompt: str


class PromptVersionResponse(BaseModel):
    id: int
    scope: str
    scope_ref: Optional[UUID]
    version: int
    title: Optional[str]
    system_prompt: str
    created_by: Optional[UUID]
    created_at: datetime
    is_active: bool


class PromptVersionActivateRequest(BaseModel):
    version_id: int