from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import redis.asyncio as aioredis

from server.app.core.constants import (
    CHANNEL_HEARTBEATS,
    CHANNEL_INTEGRITY,
    HEARTBEAT_TTL_SECONDS,
    REDIS_KEY_COMPONENT_HASH,
    REDIS_KEY_HEARTBEAT,
    ComponentStatus,
    EventType,
    Severity,
)
from server.app.core.exceptions import ComponentNotFoundException
from server.app.models.database.connection import Database
from server.app.repositories.system_repository import (
    SystemComponentRepository,
    SystemEventRepository,
)
from server.app.services.event_bus import EventBus

logger = logging.getLogger("aegis.services.integrity")


class IntegrityService:
    def __init__(
        self,
        component_repo: SystemComponentRepository | None = None,
        event_repo: SystemEventRepository | None = None,
    ):
        self.component_repo = component_repo or SystemComponentRepository()
        self.event_repo = event_repo or SystemEventRepository()
        self.event_bus = EventBus.get()

    @property
    def redis(self) -> aioredis.Redis:
        return Database.get_redis()

    async def register_component(self, data: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "component_id": data["component_id"],
            "component_type": data["component_type"],
            "device_id": data["device_id"],
            "registered_at": now,
            "expected_hash": data["expected_hash"],
            "public_key": data["public_key"],
            "last_heartbeat": None,
            "last_reported_hash": None,
            "status": ComponentStatus.OFFLINE,
            "consecutive_missed": 0,
        }
        component_id = await self.component_repo.insert_one(doc)
        component = await self.component_repo.find_by_id(component_id)

        await self.event_repo.create_event(
            event_type=EventType.COMPONENT_REGISTERED,
            severity=Severity.INFO,
            component_id=data["component_id"],
            details={"device_id": data["device_id"]},
        )
        logger.info("Component registered: %s", data["component_id"])
        return component

    async def process_heartbeat(
        self,
        component_id: str,
        timestamp: datetime,
        reported_hash: str,
        sequence_number: int = 0,
    ) -> dict[str, Any]:
        component = await self.component_repo.find_by_component_id(component_id)
        if not component:
            raise ComponentNotFoundException(component_id)

        # Store heartbeat in Redis as JSON with sequence number (TTL = 90s)
        redis_key = REDIS_KEY_HEARTBEAT.format(component_id=component_id)
        value = json.dumps({
            "sequence_number": sequence_number,
            "timestamp": timestamp.isoformat(),
        })
        await self.redis.set(redis_key, value, ex=HEARTBEAT_TTL_SECONDS)

        # Store component hash
        hash_key = REDIS_KEY_COMPONENT_HASH.format(component_id=component_id)
        await self.redis.set(hash_key, reported_hash)

        # Check hash integrity
        if component["expected_hash"] and reported_hash != component["expected_hash"]:
            logger.critical(
                "Hash mismatch for %s: expected=%s actual=%s",
                component_id,
                component["expected_hash"],
                reported_hash,
            )
            await self.component_repo.set_status(
                component_id, ComponentStatus.COMPROMISED
            )
            await self.event_repo.create_event(
                event_type=EventType.HASH_MISMATCH,
                severity=Severity.CRITICAL,
                component_id=component_id,
                details={
                    "expected": component["expected_hash"],
                    "actual": reported_hash,
                },
            )
            await self.event_bus.emit(CHANNEL_INTEGRITY, {
                "event_type": "hash_mismatch",
                "component_id": component_id,
            })
        else:
            # Update healthy status
            await self.component_repo.update_heartbeat(
                component_id, timestamp, reported_hash
            )

        await self.event_bus.emit(CHANNEL_HEARTBEATS, {
            "event_type": "heartbeat_received",
            "component_id": component_id,
            "timestamp": timestamp.isoformat(),
        })

        return {"acknowledged": True, "server_time": datetime.now(timezone.utc)}

    async def check_missed_heartbeats(self, grace_period_seconds: int = 120) -> list[str]:
        """Check all registered components for missed heartbeats.

        Returns list of component_ids that missed their heartbeat.
        """
        components = await self.component_repo.get_all_components()
        missed = []

        for comp in components:
            if comp["status"] == ComponentStatus.OFFLINE:
                continue

            comp_id = comp["component_id"]
            redis_key = REDIS_KEY_HEARTBEAT.format(component_id=comp_id)
            last_hb = await self.redis.get(redis_key)

            if last_hb is None:
                # Heartbeat expired in Redis → missed
                updated = await self.component_repo.increment_missed(comp_id)
                missed_count = updated["consecutive_missed"] if updated else 0

                logger.warning(
                    "Missed heartbeat for %s (consecutive: %d)",
                    comp_id,
                    missed_count,
                )

                await self.event_repo.create_event(
                    event_type=EventType.HEARTBEAT_MISSED,
                    severity=Severity.WARNING,
                    component_id=comp_id,
                    details={"consecutive_missed": missed_count},
                )

                # If missed too many, mark offline
                if missed_count >= 3:
                    await self.component_repo.set_status(
                        comp_id, ComponentStatus.OFFLINE
                    )
                    await self.event_repo.create_event(
                        event_type=EventType.COMPONENT_OFFLINE,
                        severity=Severity.CRITICAL,
                        component_id=comp_id,
                    )

                missed.append(comp_id)

        return missed

    async def trigger_lockdown(self, reason: str) -> None:
        logger.critical("LOCKDOWN triggered: %s", reason)
        await self.event_repo.create_event(
            event_type=EventType.LOCKDOWN_TRIGGERED,
            severity=Severity.CRITICAL,
            details={"reason": reason},
        )
        await self.event_bus.emit(CHANNEL_INTEGRITY, {
            "event_type": "lockdown",
            "reason": reason,
        })

    async def get_component(self, component_id: str) -> dict[str, Any]:
        component = await self.component_repo.find_by_component_id(component_id)
        if not component:
            raise ComponentNotFoundException(component_id)
        return component

    async def list_components(self) -> list[dict[str, Any]]:
        return await self.component_repo.get_all_components()

    async def get_status_counts(self) -> dict[str, int]:
        return await self.component_repo.get_status_counts()
