import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from celery import current_task
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.celery_app import celery_app
from app.models import Ticket, TicketStatus, TaskType, AuditLog
from app.db.session import AsyncSessionLocal
from app.services.ai_client import AzureAIClient
from app.services.mcp_client import MCPSnowflakeClient
from app.services.github_client import GitHubClient
from app.services.file_processor import FileProcessor

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_ticket")
def process_ticket_task(self, ticket_id: int) -> Dict[str, Any]:
    """
    Main task that orchestrates AI processing for a ticket.
    This is the entry point for all ticket processing.
    """
    try:
        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(process_ticket_async(ticket_id, self))
        
        return result
    except Exception as e:
        logger.error(f"Error processing ticket {ticket_id}: {str(e)}")
        # Update ticket status to failed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(mark_ticket_failed(ticket_id, str(e)))
        
        raise


async def process_ticket_async(ticket_id: int, task_instance) -> Dict[str, Any]:
    """
    Async function that handles the actual ticket processing logic.
    """
    async with AsyncSessionLocal() as db:
        # Get ticket
        ticket = await db.get(Ticket, ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")
        
        # Update status to processing
        ticket.status = TicketStatus.PROCESSING
        await db.commit()
        
        # Log start of processing
        await log_audit_event(
            db, 
            "ai_processing_started", 
            "ticket", 
            ticket_id,
            description=f"AI processing started for {ticket.task_type} task",
            metadata={"celery_task_id": task_instance.request.id}
        )
        
        # Initialize AI client
        ai_client = AzureAIClient()
        
        try:
            # Process based on task type
            if ticket.task_type == TaskType.PR_REVIEW:
                result = await process_pr_review(ticket, ai_client, db)
            elif ticket.task_type == TaskType.DOC_ANALYSIS:
                result = await process_doc_analysis(ticket, ai_client, db)
            elif ticket.task_type == TaskType.PAPER_WRITING:
                result = await process_paper_writing(ticket, ai_client, db)
            elif ticket.task_type == TaskType.SNOWFLAKE_QUERY:
                result = await process_snowflake_query(ticket, ai_client, db)
            elif ticket.task_type == TaskType.CUSTOM:
                result = await process_custom_task(ticket, ai_client, db)
            else:
                raise ValueError(f"Unknown task type: {ticket.task_type}")
            
            # Update ticket with results
            ticket.result_data = result
            ticket.status = TicketStatus.COMPLETED
            ticket.completed_at = datetime.utcnow()
            ticket.ai_model_used = ai_client.model_name
            ticket.tokens_used = result.get("tokens_used", 0)
            
            await db.commit()
            
            # Log completion
            await log_audit_event(
                db,
                "ai_processing_completed",
                "ticket",
                ticket_id,
                description=f"AI processing completed successfully",
                metadata={"tokens_used": ticket.tokens_used}
            )
            
            return {
                "status": "completed",
                "ticket_id": ticket_id,
                "result": result
            }
            
        except Exception as e:
            # Update ticket status to failed
            ticket.status = TicketStatus.FAILED
            ticket.error_message = str(e)
            await db.commit()
            
            # Log failure
            await log_audit_event(
                db,
                "ai_processing_failed",
                "ticket", 
                ticket_id,
                description=f"AI processing failed: {str(e)}",
                metadata={"error": str(e)}
            )
            
            raise


async def process_pr_review(ticket: Ticket, ai_client: AzureAIClient, db: AsyncSession) -> Dict[str, Any]:
    """Process PR review task"""
    task_data = ticket.task_data
    pr_url = task_data.get("pr_url")
    
    if not pr_url:
        raise ValueError("PR URL is required for PR review task")
    
    # Initialize GitHub client
    github_client = GitHubClient()
    
    # Fetch PR data
    pr_data = await github_client.get_pr_data(pr_url)
    
    # Prepare prompt for AI
    prompt = f"""
    Please review the following GitHub Pull Request:
    
    Title: {pr_data['title']}
    Description: {pr_data['description']}
    
    Changes:
    {pr_data['diff']}
    
    Please analyze for:
    1. Code quality and best practices
    2. Potential bugs or security issues
    3. Performance implications
    4. Suggestions for improvement
    
    Additional context: {task_data.get('additional_instructions', '')}
    """
    
    # Get AI response
    response = await ai_client.get_completion(prompt)
    
    return {
        "pr_url": pr_url,
        "review_analysis": response.content,
        "tokens_used": response.usage.total_tokens if response.usage else 0,
        "model_used": ai_client.model_name
    }


async def process_doc_analysis(ticket: Ticket, ai_client: AzureAIClient, db: AsyncSession) -> Dict[str, Any]:
    """Process document analysis task"""
    task_data = ticket.task_data
    
    # Process uploaded files
    file_processor = FileProcessor()
    extracted_content = []
    
    for attachment in ticket.attachments:
        content = await file_processor.extract_text(attachment.file_path)
        extracted_content.append({
            "filename": attachment.filename,
            "content": content
        })
    
    # Prepare prompt
    documents_text = "\n\n".join([
        f"Document: {doc['filename']}\n{doc['content']}"
        for doc in extracted_content
    ])
    
    prompt = f"""
    Please analyze the following documents:
    
    {documents_text}
    
    Analysis type: {task_data.get('analysis_type', 'general')}
    Instructions: {task_data.get('instructions', 'Provide a comprehensive analysis')}
    """
    
    # Get AI response
    response = await ai_client.get_completion(prompt)
    
    return {
        "documents_analyzed": len(extracted_content),
        "analysis": response.content,
        "tokens_used": response.usage.total_tokens if response.usage else 0,
        "model_used": ai_client.model_name
    }


async def process_paper_writing(ticket: Ticket, ai_client: AzureAIClient, db: AsyncSession) -> Dict[str, Any]:
    """Process paper writing task"""
    task_data = ticket.task_data
    
    prompt = f"""
    Please write a {task_data.get('paper_type', 'report')} on the following topic:
    
    Topic: {task_data.get('topic')}
    Requirements: {task_data.get('requirements', '')}
    Target audience: {task_data.get('target_audience', 'General')}
    Length: {task_data.get('length', 'Medium')}
    
    Additional instructions: {task_data.get('instructions', '')}
    """
    
    # Get AI response
    response = await ai_client.get_completion(prompt)
    
    return {
        "paper_content": response.content,
        "tokens_used": response.usage.total_tokens if response.usage else 0,
        "model_used": ai_client.model_name
    }


async def process_snowflake_query(ticket: Ticket, ai_client: AzureAIClient, db: AsyncSession) -> Dict[str, Any]:
    """Process Snowflake query task using MCP"""
    task_data = ticket.task_data
    query_request = task_data.get("query_request")
    
    if not query_request:
        raise ValueError("Query request is required for Snowflake task")
    
    # Initialize MCP client
    mcp_client = MCPSnowflakeClient()
    
    # Use MCP to execute query
    result = await mcp_client.execute_query(query_request)
    
    return {
        "query_request": query_request,
        "query_result": result,
        "tokens_used": 0,  # MCP doesn't use LLM tokens
        "model_used": "MCP Snowflake"
    }


async def process_custom_task(ticket: Ticket, ai_client: AzureAIClient, db: AsyncSession) -> Dict[str, Any]:
    """Process custom task"""
    task_data = ticket.task_data
    
    prompt = f"""
    Custom task request:
    
    Task description: {task_data.get('task_description')}
    Instructions: {task_data.get('instructions', '')}
    Context: {task_data.get('context', '')}
    """
    
    # Get AI response
    response = await ai_client.get_completion(prompt)
    
    return {
        "task_result": response.content,
        "tokens_used": response.usage.total_tokens if response.usage else 0,
        "model_used": ai_client.model_name
    }


async def mark_ticket_failed(ticket_id: int, error_message: str):
    """Mark ticket as failed"""
    async with AsyncSessionLocal() as db:
        ticket = await db.get(Ticket, ticket_id)
        if ticket:
            ticket.status = TicketStatus.FAILED
            ticket.error_message = error_message
            await db.commit()


async def log_audit_event(
    db: AsyncSession,
    action: str,
    entity_type: str, 
    entity_id: int,
    description: str = "",
    metadata: Optional[Dict] = None
):
    """Log audit event"""
    audit_log = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        metadata=metadata or {},
        timestamp=datetime.utcnow()
    )
    
    db.add(audit_log)
    await db.commit()