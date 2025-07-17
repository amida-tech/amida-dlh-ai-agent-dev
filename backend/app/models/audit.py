from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # What happened
    action = Column(String(100), nullable=False)  # e.g., "ticket_created", "status_changed", "ai_processing_started"
    entity_type = Column(String(50), nullable=False)  # e.g., "ticket", "user"
    entity_id = Column(Integer, nullable=False)
    
    # Who did it
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for system actions
    
    # When
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Details
    description = Column(Text)
    old_values = Column(JSON, default=dict)  # Previous state
    new_values = Column(JSON, default=dict)  # New state
    metadata = Column(JSON, default=dict)    # Additional context
    
    # IP and user agent for security
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(String(500))
    
    # Related ticket (for ticket-specific actions)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    ticket = relationship("Ticket", back_populates="audit_logs")