from __future__ import annotations

from fastapi import HTTPException, status


class AegisException(Exception):
    """Base exception for AEGIS application."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


# ── HTTP Exceptions ───────────────────────────────────────────────

class ResourceNotFoundException(HTTPException):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RESOURCE_NOT_FOUND",
                "message": f"{resource} not found",
                "details": {"resource": resource, "id": resource_id},
            },
        )


class TaskNotFoundException(HTTPException):
    def __init__(self, task_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TASK_NOT_FOUND",
                "message": "Task not found",
                "details": {"task_id": task_id},
            },
        )


class TaskAlreadyActiveException(HTTPException):
    def __init__(self, active_task_id: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "TASK_ALREADY_ACTIVE",
                "message": "Another task is already active",
                "details": {"active_task_id": active_task_id},
            },
        )


class PenaltyActiveException(HTTPException):
    def __init__(self, expires_at: str):
        super().__init__(
            status_code=423,
            detail={
                "code": "PENALTY_ACTIVE",
                "message": "Action blocked due to active penalty",
                "details": {"expires_at": expires_at},
            },
        )


class SystemLockdownException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "SYSTEM_LOCKDOWN",
                "message": "System is in lockdown mode",
            },
        )


class ValidationException(HTTPException):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": message,
                "details": details or {},
            },
        )


class ComponentNotFoundException(HTTPException):
    def __init__(self, component_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RESOURCE_NOT_FOUND",
                "message": "Component not found",
                "details": {"component_id": component_id},
            },
        )


class EvidenceNotFoundException(HTTPException):
    def __init__(self, evidence_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RESOURCE_NOT_FOUND",
                "message": "Evidence not found",
                "details": {"evidence_id": evidence_id},
            },
        )


class UserNotFoundException(HTTPException):
    def __init__(self, user_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RESOURCE_NOT_FOUND",
                "message": "User not found",
                "details": {"user_id": user_id},
            },
        )
