from fastapi import APIRouter

from app.api.v1.endpoints import tickets, users, auth, websocket

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])