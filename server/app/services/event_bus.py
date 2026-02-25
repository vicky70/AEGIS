"""In-process async event bus for decoupling components.

Provides publish/subscribe semantics. Can be swapped for Redis Pub/Sub
or a proper message broker in later phases.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

from server.app.core.constants import (
    CHANNEL_HEARTBEATS,
    CHANNEL_INTEGRITY,
    CHANNEL_NOTIFICATIONS,
    CHANNEL_PENALTIES,
    CHANNEL_TASKS,
)

logger = logging.getLogger("aegis.event_bus")

Handler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class EventBus:
    """Simple in-process async event bus."""

    _instance: EventBus | None = None
    _subscribers: dict[str, list[Handler]]

    def __init__(self) -> None:
        self._subscribers = defaultdict(list)

    @classmethod
    def get(cls) -> EventBus:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def subscribe(self, channel: str, handler: Handler) -> None:
        self._subscribers[channel].append(handler)
        logger.debug("Subscribed to %s: %s", channel, handler.__name__)

    def unsubscribe(self, channel: str, handler: Handler) -> None:
        if handler in self._subscribers[channel]:
            self._subscribers[channel].remove(handler)

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        logger.debug("Publishing to %s: %s", channel, message.get("event_type", ""))
        handlers = self._subscribers.get(channel, [])
        for handler in handlers:
            try:
                await handler(message)
            except Exception:
                logger.exception(
                    "Error in event handler %s for channel %s",
                    handler.__name__,
                    channel,
                )

    async def publish_to_redis(self, channel: str, message: dict[str, Any]) -> None:
        """Also publish to Redis Pub/Sub for cross-process communication."""
        from server.app.models.database.connection import Database

        try:
            redis = Database.get_redis()
            await redis.publish(channel, json.dumps(message, default=str))
        except Exception:
            logger.exception("Failed to publish to Redis channel %s", channel)

    async def emit(self, channel: str, message: dict[str, Any]) -> None:
        """Publish to both in-process handlers and Redis."""
        await self.publish(channel, message)
        await self.publish_to_redis(channel, message)
