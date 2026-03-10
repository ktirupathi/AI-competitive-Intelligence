"""Pydantic schemas for user settings."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserSettingsRead(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None = None
    company_name: str | None = None
    avatar_url: str | None = None
    plan: str
    plan_competitor_limit: int
    timezone: str
    briefing_frequency: str
    notification_prefs: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    company_name: str | None = Field(None, max_length=255)
    timezone: str | None = Field(None, max_length=64)
    briefing_frequency: str | None = Field(None, pattern="^(daily|weekly|monthly)$")
    notification_prefs: dict | None = None


class NotificationPrefsUpdate(BaseModel):
    email_enabled: bool | None = None
    slack_enabled: bool | None = None
    change_alerts: bool | None = None
    news_alerts: bool | None = None
    insight_alerts: bool | None = None
    briefing_delivery: bool | None = None
    alert_severity_threshold: str | None = Field(
        None, pattern="^(low|medium|high|critical)$"
    )
