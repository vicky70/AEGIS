from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import redis.asyncio as aioredis

from server.app.core.constants import (
    CHANNEL_PENALTIES,
    REDIS_KEY_PENALTY,
    EventType,
    PenaltyTriggerType,
    Severity,
)
from server.app.models.database.connection import Database
from server.app.repositories.system_repository import (
    PenaltyRepository,
    SystemEventRepository,
)
from server.app.repositories.user_repository import UserRepository
from server.app.services.event_bus import EventBus
from server.app.services.notification_service import NotificationService

logger = logging.getLogger("aegis.services.penalty")


class PenaltyService:
    def __init__(
        self,
        penalty_repo: PenaltyRepository | None = None,
        user_repo: UserRepository | None = None,
        event_repo: SystemEventRepository | None = None,
        notification_service: NotificationService | None = None,
    ):
        self.penalty_repo = penalty_repo or PenaltyRepository()
        self.user_repo = user_repo or UserRepository()
        self.event_repo = event_repo or SystemEventRepository()
        self.notification = notification_service or NotificationService()
        self.event_bus = EventBus.get()

    @property
    def redis(self) -> aioredis.Redis:
        return Database.get_redis()

    async def apply_penalty(
        self,
        user_id: str,
        reason: str,
        trigger_type: PenaltyTriggerType,
        duration_minutes: Optional[int] = None,
        trigger_details: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        # Get user default duration if not specified
        if duration_minutes is None:
            user = await self.user_repo.find_by_id(user_id)
            duration_minutes = (
                user["settings"]["penalty_duration_minutes"] if user else 30
            )

        now = datetime.now(timezone.utc)
        doc = {
            "user_id": user_id,
            "triggered_at": now,
            "duration_minutes": duration_minutes,
            "reason": reason,
            "trigger_type": trigger_type,
            "trigger_details": trigger_details or {},
            "ended_at": None,
            "early_release": False,
            "early_release_reason": None,
        }
        penalty_id = await self.penalty_repo.insert_one(doc)
        penalty = await self.penalty_repo.find_by_id(penalty_id)

        # Set in Redis with TTL
        redis_key = REDIS_KEY_PENALTY.format(user_id=user_id)
        expires_at = now + timedelta(minutes=duration_minutes)
        await self.redis.hset(redis_key, mapping={
            "penalty_id": penalty_id,
            "reason": reason,
            "expires_at": expires_at.isoformat(),
        })
        await self.redis.expireat(redis_key, expires_at)

        # Update user state
        await self.user_repo.update_state(user_id, {
            "in_penalty_box": True,
            "penalty_expires_at": expires_at,
        })

        # Events
        await self.event_repo.create_event(
            event_type=EventType.PENALTY_APPLIED,
            severity=Severity.INFO,
            user_id=user_id,
            details={"reason": reason, "duration_minutes": duration_minutes},
        )
        await self.event_bus.emit(CHANNEL_PENALTIES, {
            "event_type": "penalty_applied",
            "user_id": user_id,
            "duration_minutes": duration_minutes,
            "reason": reason,
        })
        await self.notification.notify_penalty(user_id, reason, duration_minutes)

        logger.info(
            "Penalty applied to %s: %s for %d minutes",
            user_id,
            reason,
            duration_minutes,
        )
        return penalty

    async def get_active_penalty(self, user_id: str) -> Optional[dict[str, Any]]:
        # Check Redis first (fast)
        redis_key = REDIS_KEY_PENALTY.format(user_id=user_id)
        penalty_data = await self.redis.hgetall(redis_key)
        if penalty_data:
            penalty = await self.penalty_repo.find_by_id(penalty_data["penalty_id"])
            return penalty

        # Fallback to DB
        return await self.penalty_repo.get_active_penalty(user_id)

    async def get_penalty_history(
        self, user_id: str, page: int = 1, per_page: int = 20
    ) -> tuple[list[dict[str, Any]], int]:
        skip = (page - 1) * per_page
        penalties = await self.penalty_repo.get_history(user_id, skip, per_page)
        total = await self.penalty_repo.count_by_user(user_id)
        return penalties, total

    async def clear_expired_penalties(self) -> int:
        """Find and clear expired penalties from MongoDB.

        Redis keys auto-expire, but we need to update MongoDB and user state.
        """
        expired = await self.penalty_repo.get_expired_penalties()
        cleared = 0

        for penalty in expired:
            await self.penalty_repo.end_penalty(penalty["id"])
            await self.user_repo.update_state(penalty["user_id"], {
                "in_penalty_box": False,
                "penalty_expires_at": None,
            })
            logger.info("Penalty expired for user %s", penalty["user_id"])
            cleared += 1

        return cleared
