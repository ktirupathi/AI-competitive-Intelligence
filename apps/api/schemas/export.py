"""Pydantic schemas for export and public insight pages."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PublicInsightRead(BaseModel):
    id: uuid.UUID
    category: str
    severity: str
    title: str
    summary: str
    detail: str | None = None
    recommended_action: str | None = None
    generated_at: datetime

    model_config = {"from_attributes": True}


class ExportRequest(BaseModel):
    format: str = Field(..., pattern="^(pdf|markdown|notion)$")
    briefing_id: uuid.UUID | None = None
    competitor_id: uuid.UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class ReferralCreate(BaseModel):
    referred_email: str = Field(..., max_length=320)


class ReferralRead(BaseModel):
    id: uuid.UUID
    referral_code: str
    referred_email: str | None = None
    status: str
    reward_applied: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsEvent(BaseModel):
    event_type: str = Field(
        ...,
        pattern="^(insight_view|alert_click|briefing_open|search|export)$",
    )
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
