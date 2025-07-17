from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from app.models.ticket import TicketStatus, TaskType, Priority


class TicketBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: TaskType
    priority: Priority = Priority.MEDIUM
    task_data: Dict[str, Any] = Field(default_factory=dict)


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[Priority] = None
    status: Optional[TicketStatus] = None
    task_data: Optional[Dict[str, Any]] = None
    assigned_to: Optional[int] = None


class TicketAttachmentResponse(BaseModel):
    id: int
    filename: str
    file_size: Optional[int]
    content_type: Optional[str]
    uploaded_at: datetime

    class Config:
        from_attributes = True


class TicketResponse(TicketBase):
    id: int
    status: TicketStatus
    created_by: int
    assigned_to: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    result_data: Dict[str, Any] = Field(default_factory=dict)
    processing_logs: Optional[str] = None
    error_message: Optional[str] = None
    ai_model_used: Optional[str] = None
    processing_time_seconds: int = 0
    tokens_used: int = 0
    attachments: List[TicketAttachmentResponse] = []

    class Config:
        from_attributes = True


class TicketListResponse(BaseModel):
    tickets: List[TicketResponse]
    total: int
    page: int
    per_page: int
    pages: int


class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    message: Optional[str] = None