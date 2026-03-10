"""Pydantic schemas for audit logs."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    action: str
    resource: str
    resource_id: str | None = None
    metadata_: dict | None = None
    ip_address: str | None = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]
    total: int
