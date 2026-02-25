"""Background worker: checks for missed heartbeats on a regular interval."""

from __future__ import annotations

import asyncio
import logging

from server.app.core.config import get_settings
from server.app.services.integrity_service import IntegrityService

logger = logging.getLogger("aegis.workers.heartbeat")


async def heartbeat_monitor_loop() -> None:
    """Periodically check all registered components for missed heartbeats."""
    settings = get_settings()
    interval = settings.aegis.heartbeat_interval_seconds
    grace = settings.aegis.heartbeat_grace_period_seconds
    service = IntegrityService()

    logger.info(
        "Heartbeat monitor started (interval=%ds, grace=%ds)", interval, grace
    )

    while True:
        try:
            missed = await service.check_missed_heartbeats(grace)
            if missed:
                logger.warning("Missed heartbeats: %s", missed)
        except Exception:
            logger.exception("Error in heartbeat monitor loop")

        await asyncio.sleep(interval)
