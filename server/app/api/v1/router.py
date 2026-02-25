"""Central API v1 router — aggregates all endpoint routers."""

from __future__ import annotations

from fastapi import APIRouter

from server.app.api.v1.endpoints.activity_logs import router as activity_logs_router
from server.app.api.v1.endpoints.behavioral_events import router as behavioral_events_router
from server.app.api.v1.endpoints.evidence import router as evidence_router
from server.app.api.v1.endpoints.heartbeat import router as heartbeat_router
from server.app.api.v1.endpoints.maintenance import router as maintenance_router
from server.app.api.v1.endpoints.penalties import router as penalties_router
from server.app.api.v1.endpoints.system import router as system_router
from server.app.api.v1.endpoints.tamper_events import router as tamper_events_router
from server.app.api.v1.endpoints.tasks import router as tasks_router
from server.app.api.v1.endpoints.users import router as users_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(tasks_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(evidence_router)
api_v1_router.include_router(system_router)
api_v1_router.include_router(heartbeat_router)
api_v1_router.include_router(penalties_router)
api_v1_router.include_router(activity_logs_router)
api_v1_router.include_router(tamper_events_router)
api_v1_router.include_router(behavioral_events_router)
api_v1_router.include_router(maintenance_router)
