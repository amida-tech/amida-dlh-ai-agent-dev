from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import aiofiles
import os
from datetime import datetime

from app.db.session import get_db
from app.models import Ticket, TicketAttachment, User
from app.schemas.ticket import (
    TicketCreate, 
    TicketUpdate, 
    TicketResponse, 
    TicketListResponse,
    TicketStatusUpdate
)
from app.tasks.ai_orchestrator import process_ticket_task
from app.core.config import settings

router = APIRouter()
security = HTTPBearer()


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # We'll implement this auth dependency
):
    """Create a new ticket"""
    db_ticket = Ticket(
        title=ticket.title,
        description=ticket.description,
        task_type=ticket.task_type,
        priority=ticket.priority,
        task_data=ticket.task_data,
        created_by=current_user.id
    )
    
    db.add(db_ticket)
    await db.commit()
    await db.refresh(db_ticket)
    
    # Queue the ticket for processing
    process_ticket_task.delay(db_ticket.id)
    
    return db_ticket


@router.get("/", response_model=TicketListResponse)
async def get_tickets(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    created_by: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tickets with pagination and filtering"""
    
    # Build query
    query = select(Ticket)
    
    # Apply filters
    if status:
        query = query.where(Ticket.status == status)
    if task_type:
        query = query.where(Ticket.task_type == task_type)
    if created_by:
        query = query.where(Ticket.created_by == created_by)
    
    # For non-admin users, only show their own tickets
    if current_user.role != "admin":
        query = query.where(
            (Ticket.created_by == current_user.id) | 
            (Ticket.assigned_to == current_user.id)
        )
    
    # Get total count
    count_query = select(func.count(Ticket.id))
    if status:
        count_query = count_query.where(Ticket.status == status)
    if task_type:
        count_query = count_query.where(Ticket.task_type == task_type)
    if created_by:
        count_query = count_query.where(Ticket.created_by == created_by)
    if current_user.role != "admin":
        count_query = count_query.where(
            (Ticket.created_by == current_user.id) | 
            (Ticket.assigned_to == current_user.id)
        )
    
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    query = query.order_by(Ticket.created_at.desc())
    
    result = await db.execute(query)
    tickets = result.scalars().all()
    
    pages = (total + per_page - 1) // per_page
    
    return TicketListResponse(
        tickets=tickets,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific ticket"""
    ticket = await db.get(Ticket, ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Check permissions
    if (current_user.role != "admin" and 
        ticket.created_by != current_user.id and 
        ticket.assigned_to != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this ticket"
        )
    
    return ticket


@router.put("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: int,
    ticket_update: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a ticket"""
    ticket = await db.get(Ticket, ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Check permissions
    if (current_user.role != "admin" and 
        ticket.created_by != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this ticket"
        )
    
    # Update fields
    update_data = ticket_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ticket, field, value)
    
    ticket.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(ticket)
    
    return ticket


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a ticket"""
    ticket = await db.get(Ticket, ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Check permissions - only admin or creator can delete
    if (current_user.role != "admin" and 
        ticket.created_by != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this ticket"
        )
    
    await db.delete(ticket)
    await db.commit()


@router.post("/{ticket_id}/attachments")
async def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload an attachment to a ticket"""
    ticket = await db.get(Ticket, ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Check permissions
    if (current_user.role != "admin" and 
        ticket.created_by != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to upload attachments to this ticket"
        )
    
    # Check file size
    if file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum of {settings.MAX_FILE_SIZE} bytes"
        )
    
    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(ticket_id))
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, file.filename)
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    
    # Create attachment record
    attachment = TicketAttachment(
        ticket_id=ticket_id,
        filename=file.filename,
        file_path=file_path,
        file_size=file.size,
        content_type=file.content_type
    )
    
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    
    return {
        "message": "File uploaded successfully",
        "attachment_id": attachment.id,
        "filename": attachment.filename
    }


@router.post("/{ticket_id}/reprocess")
async def reprocess_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reprocess a ticket"""
    ticket = await db.get(Ticket, ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Check permissions
    if (current_user.role != "admin" and 
        ticket.created_by != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to reprocess this ticket"
        )
    
    # Reset ticket status
    ticket.status = "pending"
    ticket.error_message = None
    ticket.result_data = {}
    ticket.updated_at = datetime.utcnow()
    
    await db.commit()
    
    # Queue for processing again
    process_ticket_task.delay(ticket_id)
    
    return {"message": "Ticket queued for reprocessing"}


# Placeholder for auth dependency - we'll implement this next
async def get_current_user():
    # This will be implemented when we add authentication
    pass