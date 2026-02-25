from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ── Nested Schemas ────────────────────────────────────────────────

class RawWindowsEventCreate(BaseModel):
    source: str
    log: str
    message: str
    record_number: int
    computer_name: str


# ── Request Schemas ───────────────────────────────────────────────

class TamperEventCreate(BaseModel):
    timestamp: datetime
    event_id: int  # 4656|7034|7036|7040
    event_type: str
    severity: str
    service_state: Optional[str] = None
    maintenance_window_id: Optional[str] = None
    classified_as: Optional[str] = None
    raw_event: RawWindowsEventCreate
    component_id: str = "desktop_client_main"


# ── Response Schemas ──────────────────────────────────────────────

class TamperEventResponse(BaseModel):
    id: str
    timestamp: datetime
    event_id: int
    event_type: str
    severity: str
    service_state: Optional[str]
    maintenance_window_id: Optional[str]
    classified_as: Optional[str] = None
    raw_event: RawWindowsEventCreate
    component_id: str
