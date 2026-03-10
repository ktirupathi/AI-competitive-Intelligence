"""Pydantic schemas for alerts."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class AlertRead(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    competitor_id: uuid.UUID | None = None
    alert_type: str
    severity: str
    title: str
    summary: str | None = None
    significance_score: float
    delivered_via: list | None = None
    delivered_at: datetime | None = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    items: list[AlertRead]
    total: int


class AlertMarkRead(BaseModel):
    alert_ids: list[uuid.UUID]
