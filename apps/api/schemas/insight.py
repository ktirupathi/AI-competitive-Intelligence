"""Pydantic schemas for insights."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class InsightRead(BaseModel):
    id: uuid.UUID
    competitor_id: uuid.UUID
    category: str
    severity: str
    confidence: float
    title: str
    summary: str
    detail: str | None = None
    recommended_action: str | None = None
    source_refs: dict | None = None
    is_read: bool
    is_dismissed: bool
    generated_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class InsightListResponse(BaseModel):
    items: list[InsightRead]
    total: int


class InsightMarkRead(BaseModel):
    insight_ids: list[uuid.UUID]


class InsightDismiss(BaseModel):
    insight_ids: list[uuid.UUID]


class InsightFilters(BaseModel):
    competitor_id: uuid.UUID | None = None
    category: str | None = None
    severity: str | None = None
    is_read: bool | None = None
    is_dismissed: bool | None = None
