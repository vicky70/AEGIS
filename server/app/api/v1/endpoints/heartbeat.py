from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from server.app.api.dependencies import get_integrity_service
from server.app.models.schemas.common import SuccessResponse
from server.app.models.schemas.system_schemas import (
    HeartbeatRequest,
    HeartbeatResponse,
)
from server.app.services.integrity_service import IntegrityService

router = APIRouter(prefix="/system", tags=["heartbeat"])


@router.post("/heartbeat", response_model=SuccessResponse[HeartbeatResponse])
async def receive_heartbeat(
    data: HeartbeatRequest,
    service: IntegrityService = Depends(get_integrity_service),
):
    result = await service.process_heartbeat(
        component_id=data.component_id,
        timestamp=data.timestamp,
        reported_hash=data.hash or "",
        sequence_number=data.sequence_number,
    )
    return SuccessResponse(data=HeartbeatResponse(
        acknowledged=result["acknowledged"],
        server_time=result["server_time"],
    ))
