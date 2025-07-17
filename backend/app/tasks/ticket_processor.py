import asyncio
from datetime import datetime
from typing import Dict, Any

from app.tasks.celery_app import celery_app
from app.models import Ticket, TicketStatus
from app.db.session import AsyncSessionLocal


@celery_app.task(name="update_ticket_status")
def update_ticket_status_task(ticket_id: int, status: str, result_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Task to update ticket status and results.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    result = loop.run_until_complete(update_ticket_status_async(ticket_id, status, result_data))
    return result


async def update_ticket_status_async(ticket_id: int, status: str, result_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Update ticket status asynchronously.
    """
    async with AsyncSessionLocal() as db:
        ticket = await db.get(Ticket, ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")
        
        # Update status
        ticket.status = TicketStatus(status)
        ticket.updated_at = datetime.utcnow()
        
        # Update result data if provided
        if result_data:
            ticket.result_data = result_data
        
        # Set completion time if completed
        if status == TicketStatus.COMPLETED:
            ticket.completed_at = datetime.utcnow()
        
        await db.commit()
        
        return {
            "ticket_id": ticket_id,
            "status": status,
            "updated_at": ticket.updated_at.isoformat()
        }


@celery_app.task(name="cleanup_old_tickets")
def cleanup_old_tickets_task(days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old completed tickets (optional maintenance task).
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    result = loop.run_until_complete(cleanup_old_tickets_async(days_old))
    return result


async def cleanup_old_tickets_async(days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old tickets asynchronously.
    """
    from sqlalchemy import select, func
    from datetime import timedelta
    
    async with AsyncSessionLocal() as db:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Count tickets to be cleaned
        count_query = select(func.count(Ticket.id)).where(
            Ticket.status == TicketStatus.COMPLETED,
            Ticket.completed_at < cutoff_date
        )
        
        result = await db.execute(count_query)
        count = result.scalar_one()
        
        # For now, just return count - implement actual cleanup logic as needed
        return {
            "tickets_found": count,
            "cutoff_date": cutoff_date.isoformat(),
            "action": "counted_only"  # Change to "deleted" when implementing deletion
        }