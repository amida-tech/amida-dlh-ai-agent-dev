from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
import enum

from app.db.base import Base


class TicketStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, enum.Enum):
    PR_REVIEW = "pr_review"
    DOC_ANALYSIS = "doc_analysis"
    PAPER_WRITING = "paper_writing"
    SNOWFLAKE_QUERY = "snowflake_query"
    CUSTOM = "custom"


class Priority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    task_type = Column(Enum(TaskType), nullable=False)
    priority = Column(Enum(Priority), default=Priority.MEDIUM)
    status = Column(Enum(TicketStatus), default=TicketStatus.PENDING)
    
    # User who created the ticket
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Task-specific data (JSON field for flexibility)
    task_data = Column(JSON, default=dict)
    
    # Results and processing info
    result_data = Column(JSON, default=dict)
    processing_logs = Column(Text)
    error_message = Column(Text, nullable=True)
    
    # AI processing metadata
    ai_model_used = Column(String(100))
    processing_time_seconds = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_tickets")
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_tickets")
    attachments = relationship("TicketAttachment", back_populates="ticket", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="ticket", cascade="all, delete-orphan")


class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    content_type = Column(String(100))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    ticket = relationship("Ticket", back_populates="attachments")