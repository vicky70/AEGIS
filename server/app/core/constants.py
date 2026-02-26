from __future__ import annotations

from enum import IntEnum, StrEnum


# ── Task ──────────────────────────────────────────────────────────

class TaskCategory(StrEnum):
    WORK = "work"
    HEALTH = "health"
    LEARNING = "learning"
    PERSONAL = "personal"
    CHORE = "chore"


class TaskStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    OVERDUE = "overdue"
    SKIPPED = "skipped"


class VerificationMethod(StrEnum):
    ACTIVITY_LOG = "activity_log"
    SCREENSHOT = "screenshot"
    API_CHECK = "api_check"
    LOCATION = "location"
    MANUAL = "manual"
    MULTI = "multi"


class RecurrencePattern(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


# ── Evidence ──────────────────────────────────────────────────────

class EvidenceType(StrEnum):
    SCREENSHOT = "screenshot"
    ACTIVITY_LOG = "activity_log"
    API_RESPONSE = "api_response"
    LOCATION_TRACE = "location_trace"
    USER_NOTE = "user_note"


# ── System Components ─────────────────────────────────────────────

class ComponentType(StrEnum):
    DESKTOP_CLIENT = "desktop_client"
    MOBILE_CLIENT = "mobile_client"
    NETWORK_FILTER = "network_filter"
    SERVER_WORKER = "server_worker"


class ComponentStatus(StrEnum):
    HEALTHY = "healthy"
    WARNING = "warning"
    COMPROMISED = "compromised"
    OFFLINE = "offline"


# ── System Events ─────────────────────────────────────────────────

class EventType(StrEnum):
    HEARTBEAT_MISSED = "heartbeat_missed"
    HASH_MISMATCH = "hash_mismatch"
    LOCKDOWN_TRIGGERED = "lockdown_triggered"
    PENALTY_APPLIED = "penalty_applied"
    TASK_VERIFIED = "task_verified"
    COMPONENT_REGISTERED = "component_registered"
    COMPONENT_OFFLINE = "component_offline"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ── Penalties ─────────────────────────────────────────────────────

class PenaltyTriggerType(StrEnum):
    BLOCKED_SITE_ACCESS = "blocked_site_access"
    TASK_FAILURE = "task_failure"
    INTEGRITY_VIOLATION = "integrity_violation"


# ── Notification Preferences ──────────────────────────────────────

class NotificationPreference(StrEnum):
    VOICE = "voice"
    VISUAL = "visual"
    BOTH = "both"


# ── App Categories ────────────────────────────────────────────────

class AppCategory(StrEnum):
    PRODUCTIVE = "productive"
    COMMUNICATION = "communication"
    DISTRACTION = "distraction"
    NEUTRAL = "neutral"
    DISTRACTING = "distracting"  # legacy alias for distraction


# ── Tamper / Desktop Monitoring ───────────────────────────────────

class TamperEventId(IntEnum):
    ACCESS_DENIED = 4656
    SERVICE_CRASHED = 7034
    SERVICE_STATE_CHANGE = 7036
    STARTUP_TYPE_CHANGED = 7040


class TamperEventType(StrEnum):
    STOP_ATTEMPT_DENIED = "stop_attempt_denied"
    SERVICE_STATE_CHANGE = "service_state_change"
    CRASH = "crash"
    STARTUP_TYPE_CHANGED = "startup_type_changed"


class TamperClassification(StrEnum):
    INTENDED_MAINTENANCE = "intended_maintenance"
    UNEXPECTED_STOP = "unexpected_stop"
    TAMPER_ATTEMPT = "tamper_attempt"


class ServiceState(StrEnum):
    STOPPED = "stopped"
    RUNNING = "running"


class BehavioralEventType(StrEnum):
    STOP_ATTEMPT_DENIED = "stop_attempt_denied"


class MaintenanceWindowStatus(StrEnum):
    DECLARED = "declared"
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"


# ── Redis Key Patterns ────────────────────────────────────────────

REDIS_KEY_HEARTBEAT = "heartbeat:{component_id}"
REDIS_KEY_PENALTY = "penalty:{user_id}"
REDIS_KEY_SESSION = "session:{session_id}"
REDIS_KEY_COMPONENT_HASH = "component:hash:{component_id}"
REDIS_KEY_TASK_ACTIVE = "task:active:{user_id}"
REDIS_KEY_USER_STATE = "user:state:{user_id}"
REDIS_KEY_LOCK = "lock:{resource}"

# ── Redis Pub/Sub Channels ────────────────────────────────────────

CHANNEL_HEARTBEATS = "aegis:heartbeats"
CHANNEL_PENALTIES = "aegis:penalties"
CHANNEL_TASKS = "aegis:tasks"
CHANNEL_INTEGRITY = "aegis:integrity"
CHANNEL_NOTIFICATIONS = "aegis:notifications:{user_id}"

# ── Defaults ──────────────────────────────────────────────────────

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
HEARTBEAT_TTL_SECONDS = 90
SESSION_TTL_SECONDS = 86400  # 24 hours
LOCK_TTL_SECONDS = 30
