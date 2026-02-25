"""FastAPI dependency injection for services, repos, and user context."""

from __future__ import annotations

from server.app.repositories.activity_log_repository import ActivityLogRepository
from server.app.repositories.behavioral_event_repository import BehavioralEventRepository
from server.app.repositories.evidence_repository import EvidenceRepository
from server.app.repositories.maintenance_window_repository import MaintenanceWindowRepository
from server.app.repositories.system_repository import (
    PenaltyRepository,
    SystemComponentRepository,
    SystemEventRepository,
)
from server.app.repositories.tamper_event_repository import TamperEventRepository
from server.app.repositories.task_repository import TaskRepository
from server.app.repositories.user_repository import UserRepository
from server.app.services.activity_log_service import ActivityLogService
from server.app.services.behavioral_event_service import BehavioralEventService
from server.app.services.integrity_service import IntegrityService
from server.app.services.maintenance_service import MaintenanceService
from server.app.services.notification_service import NotificationService
from server.app.services.penalty_service import PenaltyService
from server.app.services.scheduler_service import SchedulerService
from server.app.services.tamper_event_service import TamperEventService
from server.app.services.task_service import TaskService


# ── Repository Providers ──────────────────────────────────────────

def get_task_repo() -> TaskRepository:
    return TaskRepository()


def get_user_repo() -> UserRepository:
    return UserRepository()


def get_evidence_repo() -> EvidenceRepository:
    return EvidenceRepository()


def get_component_repo() -> SystemComponentRepository:
    return SystemComponentRepository()


def get_event_repo() -> SystemEventRepository:
    return SystemEventRepository()


def get_penalty_repo() -> PenaltyRepository:
    return PenaltyRepository()


def get_activity_log_repo() -> ActivityLogRepository:
    return ActivityLogRepository()


def get_tamper_event_repo() -> TamperEventRepository:
    return TamperEventRepository()


def get_behavioral_event_repo() -> BehavioralEventRepository:
    return BehavioralEventRepository()


def get_maintenance_window_repo() -> MaintenanceWindowRepository:
    return MaintenanceWindowRepository()


# ── Service Providers ─────────────────────────────────────────────

def get_task_service() -> TaskService:
    return TaskService()


def get_scheduler_service() -> SchedulerService:
    return SchedulerService()


def get_integrity_service() -> IntegrityService:
    return IntegrityService()


def get_notification_service() -> NotificationService:
    return NotificationService()


def get_penalty_service() -> PenaltyService:
    return PenaltyService()


def get_activity_log_service() -> ActivityLogService:
    return ActivityLogService()


def get_tamper_event_service() -> TamperEventService:
    return TamperEventService()


def get_behavioral_event_service() -> BehavioralEventService:
    return BehavioralEventService()


def get_maintenance_service() -> MaintenanceService:
    return MaintenanceService()


# ── Placeholder user context ─────────────────────────────────────
# Since login/signup is removed, we use a fixed default user ID.
# This can be replaced with real JWT auth in a later phase.

DEFAULT_USER_ID = "000000000000000000000001"
DEFAULT_USERNAME = "aegis_user"


async def get_current_user_id() -> str:
    """Return the default user ID (no auth required in this phase)."""
    return DEFAULT_USER_ID
