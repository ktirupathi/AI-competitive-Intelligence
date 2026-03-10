"""Service layer for real-time alerts."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.alert import Alert
from ..models.integration import Integration

logger = logging.getLogger(__name__)


class AlertService:
    """Handles alert creation, delivery, and management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_alert(
        self,
        workspace_id: uuid.UUID,
        alert_type: str,
        title: str,
        severity: str = "medium",
        summary: str | None = None,
        significance_score: float = 0.5,
        competitor_id: uuid.UUID | None = None,
        source_type: str | None = None,
        source_id: uuid.UUID | None = None,
    ) -> Alert:
        """Create a new alert."""
        alert = Alert(
            workspace_id=workspace_id,
            competitor_id=competitor_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            summary=summary,
            significance_score=significance_score,
            source_type=source_type,
            source_id=source_id,
        )
        self.db.add(alert)
        await self.db.flush()
        await self.db.refresh(alert)
        logger.info("Created alert %s for workspace %s", alert.id, workspace_id)
        return alert

    async def list_alerts(
        self,
        workspace_id: uuid.UUID,
        severity: str | None = None,
        alert_type: str | None = None,
        is_read: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Alert], int]:
        """List alerts for a workspace with filters."""
        base = select(Alert).where(Alert.workspace_id == workspace_id)

        if severity:
            base = base.where(Alert.severity == severity)
        if alert_type:
            base = base.where(Alert.alert_type == alert_type)
        if is_read is not None:
            base = base.where(Alert.is_read == is_read)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        query = base.order_by(Alert.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def mark_read(
        self, alert_ids: list[uuid.UUID], workspace_id: uuid.UUID
    ) -> int:
        """Mark alerts as read."""
        from sqlalchemy import update

        stmt = (
            update(Alert)
            .where(
                Alert.id.in_(alert_ids),
                Alert.workspace_id == workspace_id,
            )
            .values(is_read=True)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

    async def should_alert(
        self,
        severity: str,
        significance_score: float,
    ) -> bool:
        """Determine if a change warrants an alert."""
        if severity in ("high", "critical"):
            return True
        if significance_score >= 0.8:
            return True
        return False
