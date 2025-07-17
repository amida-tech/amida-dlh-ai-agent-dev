import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.websocket_manager import manager
from app.services.auth import get_current_user_from_token
from app.models import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/{token}")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time updates
    Authentication is done via token in URL path
    """
    try:
        # Authenticate user from token
        user = await get_current_user_from_token(token, db)
        
        if not user or not user.is_active:
            await websocket.close(code=4001, reason="Authentication failed")
            return
        
        # Connect user
        await manager.connect(websocket, user.id)
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    await manager.handle_client_message(websocket, message)
                except json.JSONDecodeError:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }, websocket)
                except Exception as e:
                    logger.error(f"Error handling client message: {str(e)}")
                    await manager.send_personal_message({
                        "type": "error", 
                        "message": "Error processing message"
                    }, websocket)
        
        except WebSocketDisconnect:
            logger.info(f"User {user.id} disconnected")
        
        except Exception as e:
            logger.error(f"WebSocket error for user {user.id}: {str(e)}")
        
        finally:
            manager.disconnect(websocket)
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")
        await websocket.close(code=4000, reason="Connection error")


@router.get("/ws/status")
async def websocket_status():
    """
    Get WebSocket connection status (admin endpoint)
    """
    return {
        "total_connections": manager.get_connection_count(),
        "connected_users": manager.get_connected_users(),
        "status": "active"
    }


# Utility function to send notifications from other parts of the app
async def notify_ticket_update(ticket_id: int, update_data: dict, user_id: int = None):
    """
    Send ticket update notification via WebSocket
    Can be called from other parts of the application
    """
    await manager.send_ticket_update(ticket_id, update_data, user_id)


async def notify_processing_status(ticket_id: int, status: str, user_id: int, details: dict = None):
    """
    Send processing status notification via WebSocket
    """
    await manager.send_processing_status(ticket_id, status, user_id, details)


async def notify_error(ticket_id: int, error_message: str, user_id: int):
    """
    Send error notification via WebSocket
    """
    await manager.send_error_notification(ticket_id, error_message, user_id)