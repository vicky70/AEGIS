from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from server.app.core.constants import CHANNEL_NOTIFICATIONS
from server.app.services.event_bus import EventBus

logger = logging.getLogger("aegis.services.notification")


class ConnectionManager:
    """Manages WebSocket connections per user."""

    def __init__(self) -> None:
        self._connections: dict[str, list[Any]] = {}

    def connect(self, user_id: str, websocket: Any) -> None:
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(websocket)
        logger.info("WebSocket connected for user %s", user_id)

    def disconnect(self, user_id: str, websocket: Any) -> None:
        if user_id in self._connections:
            self._connections[user_id] = [
                ws for ws in self._connections[user_id] if ws is not websocket
            ]
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info("WebSocket disconnected for user %s", user_id)

    async def send_to_user(self, user_id: str, message: dict[str, Any]) -> None:
        connections = self._connections.get(user_id, [])
        dead: list[Any] = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    async def broadcast(self, message: dict[str, Any]) -> None:
        for user_id in list(self._connections.keys()):
            await self.send_to_user(user_id, message)

    @property
    def active_count(self) -> int:
        return sum(len(conns) for conns in self._connections.values())


# Singleton
connection_manager = ConnectionManager()


class NotificationService:
    def __init__(self) -> None:
        self.event_bus = EventBus.get()
        self.manager = connection_manager

    async def notify_user(self, user_id: str, notification: dict[str, Any]) -> None:
        message = {
            "type": "notification",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **notification,
        }
        await self.manager.send_to_user(user_id, message)

        await self.event_bus.emit(
            CHANNEL_NOTIFICATIONS.format(user_id=user_id),
            message,
        )

    async def broadcast(self, notification: dict[str, Any]) -> None:
        message = {
            "type": "broadcast",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **notification,
        }
        await self.manager.broadcast(message)

    async def notify_penalty(
        self, user_id: str, reason: str, duration_minutes: int
    ) -> None:
        await self.notify_user(user_id, {
            "event": "penalty_applied",
            "reason": reason,
            "duration_minutes": duration_minutes,
        })

    async def notify_task_state(
        self, user_id: str, task_id: str, new_status: str
    ) -> None:
        await self.notify_user(user_id, {
            "event": "task_state_changed",
            "task_id": task_id,
            "status": new_status,
        })
