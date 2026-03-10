"""Pydantic schemas for briefings."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class BriefingRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    frequency: str
    executive_summary: str | None = None
    full_content: str | None = None
    sections: dict | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    status: str
    sent_at: datetime | None = None
    delivery_channels: list | None = None
    competitor_count: int
    insight_count: int
    change_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class BriefingListResponse(BaseModel):
    items: list[BriefingRead]
    total: int


class BriefingSummary(BaseModel):
    id: uuid.UUID
    title: str
    frequency: str
    executive_summary: str | None = None
    status: str
    period_start: datetime | None = None
    period_end: datetime | None = None
    competitor_count: int
    insight_count: int
    change_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class BriefingGenerateRequest(BaseModel):
    """Manually trigger briefing generation."""
    competitor_ids: list[uuid.UUID] | None = None  # None means all competitors
    frequency: str = "weekly"
