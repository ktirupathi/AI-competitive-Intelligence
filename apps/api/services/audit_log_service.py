"""Service layer for audit logging."""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditLogService:
    """Handles creating and querying audit log entries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: str,
        resource: str,
        user_id: uuid.UUID | None = None,
        workspace_id: uuid.UUID | None = None,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        entry = AuditLog(
            workspace_id=workspace_id,
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            metadata_=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list_logs(
        self,
        workspace_id: uuid.UUID,
        action: str | None = None,
        resource: str | None = None,
        user_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """List audit logs for a workspace with optional filters."""
        from sqlalchemy import func

        base = select(AuditLog).where(AuditLog.workspace_id == workspace_id)

        if action:
            base = base.where(AuditLog.action == action)
        if resource:
            base = base.where(AuditLog.resource == resource)
        if user_id:
            base = base.where(AuditLog.user_id == user_id)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        query = base.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total


async def log_action(
    db: AsyncSession,
    action: str,
    resource: str,
    user_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Convenience function to log an audit action."""
    service = AuditLogService(db)
    return await service.log(
        action=action,
        resource=resource,
        user_id=user_id,
        workspace_id=workspace_id,
        resource_id=resource_id,
        metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
    )
