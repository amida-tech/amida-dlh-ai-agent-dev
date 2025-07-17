import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

from app.models import User

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket connection manager for real-time updates
    """
    
    def __init__(self):
        # Store active connections: user_id -> set of websockets
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Store websocket -> user mapping for cleanup
        self.websocket_users: Dict[WebSocket, int] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """
        Accept WebSocket connection and add to active connections
        """
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.websocket_users[websocket] = user_id
        
        logger.info(f"User {user_id} connected via WebSocket")
        
        # Send connection confirmation
        await self.send_personal_message({
            "type": "connection_confirmed",
            "message": "WebSocket connection established",
            "user_id": user_id
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove WebSocket connection
        """
        if websocket in self.websocket_users:
            user_id = self.websocket_users[websocket]
            
            # Remove from active connections
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                
                # Remove user entry if no more connections
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove from websocket mapping
            del self.websocket_users[websocket]
            
            logger.info(f"User {user_id} disconnected from WebSocket")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send message to a specific WebSocket connection
        """
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message to websocket: {str(e)}")
            # Remove broken connection
            self.disconnect(websocket)
    
    async def send_message_to_user(self, message: dict, user_id: int):
        """
        Send message to all WebSocket connections for a specific user
        """
        if user_id in self.active_connections:
            disconnected_websockets = []
            
            for websocket in self.active_connections[user_id].copy():
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {str(e)}")
                    disconnected_websockets.append(websocket)
            
            # Clean up disconnected websockets
            for websocket in disconnected_websockets:
                self.disconnect(websocket)
    
    async def broadcast_to_all(self, message: dict):
        """
        Send message to all connected users
        """
        disconnected_websockets = []
        
        for user_id, websockets in self.active_connections.items():
            for websocket in websockets.copy():
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {str(e)}")
                    disconnected_websockets.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected_websockets:
            self.disconnect(websocket)
    
    async def send_ticket_update(self, ticket_id: int, update_data: dict, user_id: int = None):
        """
        Send ticket update notification
        """
        message = {
            "type": "ticket_update",
            "ticket_id": ticket_id,
            "data": update_data,
            "timestamp": update_data.get("timestamp")
        }
        
        if user_id:
            # Send to specific user
            await self.send_message_to_user(message, user_id)
        else:
            # Broadcast to all users (for admin notifications)
            await self.broadcast_to_all(message)
    
    async def send_processing_status(self, ticket_id: int, status: str, user_id: int, details: dict = None):
        """
        Send processing status update
        """
        message = {
            "type": "processing_status",
            "ticket_id": ticket_id,
            "status": status,
            "details": details or {},
            "timestamp": details.get("timestamp") if details else None
        }
        
        await self.send_message_to_user(message, user_id)
    
    async def send_error_notification(self, ticket_id: int, error_message: str, user_id: int):
        """
        Send error notification
        """
        message = {
            "type": "error_notification",
            "ticket_id": ticket_id,
            "error": error_message,
            "timestamp": None  # Will be set by client
        }
        
        await self.send_message_to_user(message, user_id)
    
    def get_connection_count(self) -> int:
        """
        Get total number of active connections
        """
        total = sum(len(websockets) for websockets in self.active_connections.values())
        return total
    
    def get_connected_users(self) -> List[int]:
        """
        Get list of connected user IDs
        """
        return list(self.active_connections.keys())
    
    async def handle_client_message(self, websocket: WebSocket, message: dict):
        """
        Handle incoming message from client
        """
        message_type = message.get("type")
        
        if message_type == "ping":
            # Respond to ping with pong
            await self.send_personal_message({
                "type": "pong",
                "timestamp": message.get("timestamp")
            }, websocket)
        
        elif message_type == "subscribe_ticket":
            # Subscribe to specific ticket updates
            ticket_id = message.get("ticket_id")
            user_id = self.websocket_users.get(websocket)
            
            if ticket_id and user_id:
                logger.info(f"User {user_id} subscribed to ticket {ticket_id} updates")
                await self.send_personal_message({
                    "type": "subscription_confirmed",
                    "ticket_id": ticket_id
                }, websocket)
        
        else:
            logger.warning(f"Unknown message type: {message_type}")


# Global connection manager instance
manager = ConnectionManager()