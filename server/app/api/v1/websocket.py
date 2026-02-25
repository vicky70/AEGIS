"""WebSocket endpoint for real-time notifications."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.app.api.dependencies import DEFAULT_USER_ID
from server.app.services.notification_service import connection_manager

logger = logging.getLogger("aegis.ws")

ws_router = APIRouter()


@ws_router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    connection_manager.connect(user_id, websocket)

    try:
        while True:
            # Keep connection alive; clients can send pings
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "subscribe":
                # Future: subscribe to specific channels
                await websocket.send_json({
                    "type": "subscribed",
                    "channel": data.get("channel", "default"),
                })
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                })
    except WebSocketDisconnect:
        connection_manager.disconnect(user_id, websocket)
        logger.info("WebSocket disconnected: user=%s", user_id)
    except Exception:
        connection_manager.disconnect(user_id, websocket)
        logger.exception("WebSocket error for user=%s", user_id)


@ws_router.websocket("/ws")
async def websocket_default(websocket: WebSocket):
    """Default WebSocket using the default user."""
    await websocket_endpoint(websocket, DEFAULT_USER_ID)
