from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RawWindowsEvent(BaseModel):
    source: str
    log: str
    message: str
    record_number: int
    computer_name: str


class TamperEvent(BaseModel):
    id: str
    timestamp: datetime
    event_id: int  # 4656|7034|7036|7040
    event_type: str
    severity: str
    service_state: Optional[str] = None  # "stopped"|"running"|null
    maintenance_window_id: Optional[str] = None
    classified_as: str
    raw_event: RawWindowsEvent
    component_id: str
