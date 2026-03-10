"""Pydantic schemas for workspaces."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    plan: str = Field(default="starter", pattern="^(starter|growth|enterprise)$")


class WorkspaceRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    owner_id: uuid.UUID
    plan: str
    logo_url: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceListResponse(BaseModel):
    items: list[WorkspaceRead]


class WorkspaceMemberRead(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID | None = None
    role: str
    invited_email: str | None = None
    invite_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceInvite(BaseModel):
    email: str = Field(..., max_length=320)
    role: str = Field(default="member", pattern="^(admin|member|viewer)$")


class WorkspaceUsageRead(BaseModel):
    workspace_id: uuid.UUID
    competitors_count: int
    briefings_generated: int
    alerts_sent: int
    searches_performed: int
    api_calls: int
    max_competitors: int
    max_briefings_per_month: int
    max_alerts_per_month: int
    max_searches_per_month: int
    period_start: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemberRoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(admin|member|viewer)$")
