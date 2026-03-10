"""Pydantic schemas for integrations."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class IntegrationBase(BaseModel):
    type: str = Field(..., pattern="^(slack|email|webhook)$")
    is_active: bool = True
    event_filters: dict | None = None
    config: dict | None = None


class SlackIntegrationCreate(IntegrationBase):
    type: str = "slack"
    slack_channel_id: str
    slack_workspace_id: str | None = None


class EmailIntegrationCreate(IntegrationBase):
    type: str = "email"
    email_address: str = Field(..., max_length=320)


class WebhookIntegrationCreate(IntegrationBase):
    type: str = "webhook"
    webhook_url: str


class IntegrationUpdate(BaseModel):
    is_active: bool | None = None
    event_filters: dict | None = None
    config: dict | None = None
    slack_channel_id: str | None = None
    email_address: str | None = None
    webhook_url: str | None = None


class IntegrationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    is_active: bool
    slack_channel_id: str | None = None
    slack_workspace_id: str | None = None
    email_address: str | None = None
    webhook_url: str | None = None
    event_filters: dict | None = None
    config: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IntegrationListResponse(BaseModel):
    items: list[IntegrationRead]
    total: int


class SlackOAuthRequest(BaseModel):
    code: str
    redirect_uri: str


class IntegrationTestResult(BaseModel):
    success: bool
    message: str
