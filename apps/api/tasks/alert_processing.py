"""Celery tasks for real-time alert processing and delivery."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from ..celery_app import celery
from ..config import get_settings
from ..database import async_session_factory
from ..models.alert import Alert, AgentRun
from ..models.change import Change
from ..models.competitor import Competitor
from ..models.insight import Insight
from ..models.integration import Integration
from ..models.workspace import Workspace
from ..services.alert_service import AlertService

logger = logging.getLogger(__name__)
settings = get_settings()


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery.task(
    name="apps.api.tasks.alert_processing.check_and_send_alerts",
    max_retries=3,
    default_retry_delay=60,
)
def check_and_send_alerts():
    """Check for significant changes and send alerts to configured channels."""
    logger.info("Starting alert processing cycle")
    _run_async(_process_alerts())
    logger.info("Alert processing cycle complete")


@celery.task(
    name="apps.api.tasks.alert_processing.send_single_alert",
    max_retries=3,
    default_retry_delay=30,
)
def send_single_alert(alert_id: str):
    """Deliver a single alert via configured channels."""
    _run_async(_deliver_alert(uuid.UUID(alert_id)))


async def _process_alerts():
    """Scan for recent high-significance changes and create alerts."""
    started_at = datetime.now(timezone.utc)
    agent_run = None

    async with async_session_factory() as db:
        # Track this run
        agent_run = AgentRun(
            agent_name="alert_processing",
            status="running",
            started_at=started_at,
        )
        db.add(agent_run)
        await db.flush()

        try:
            # Find recent changes that haven't been alerted on yet
            # Look for high/critical severity changes in the last hour
            from datetime import timedelta

            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

            changes_q = (
                select(Change)
                .where(
                    Change.detected_at >= cutoff,
                    Change.severity.in_(["high", "critical"]),
                )
                .order_by(Change.significance_score.desc())
                .limit(50)
            )
            result = await db.execute(changes_q)
            changes = list(result.scalars().all())

            items_processed = 0
            for change in changes:
                # Get the competitor to find the workspace
                comp_result = await db.execute(
                    select(Competitor).where(Competitor.id == change.competitor_id)
                )
                competitor = comp_result.scalar_one_or_none()
                if not competitor or not competitor.workspace_id:
                    continue

                # Check if alert already exists for this change
                existing = await db.execute(
                    select(Alert).where(
                        Alert.source_type == "change",
                        Alert.source_id == change.id,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                service = AlertService(db)
                alert = await service.create_alert(
                    workspace_id=competitor.workspace_id,
                    alert_type="change",
                    title=f"[{change.severity.upper()}] {change.title}",
                    severity=change.severity,
                    summary=change.summary,
                    significance_score=change.significance_score,
                    competitor_id=competitor.id,
                    source_type="change",
                    source_id=change.id,
                )
                items_processed += 1

                # Queue delivery
                send_single_alert.delay(str(alert.id))

            # Also check for high-severity insights
            insights_q = (
                select(Insight)
                .where(
                    Insight.created_at >= cutoff,
                    Insight.severity.in_(["high", "critical"]),
                )
                .limit(20)
            )
            insight_result = await db.execute(insights_q)
            insights = list(insight_result.scalars().all())

            for insight in insights:
                comp_result = await db.execute(
                    select(Competitor).where(Competitor.id == insight.competitor_id)
                )
                competitor = comp_result.scalar_one_or_none()
                if not competitor or not competitor.workspace_id:
                    continue

                existing = await db.execute(
                    select(Alert).where(
                        Alert.source_type == "insight",
                        Alert.source_id == insight.id,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                service = AlertService(db)
                alert = await service.create_alert(
                    workspace_id=competitor.workspace_id,
                    alert_type="insight",
                    title=f"New insight: {insight.title}",
                    severity=insight.severity,
                    summary=insight.summary,
                    significance_score=insight.confidence,
                    competitor_id=competitor.id,
                    source_type="insight",
                    source_id=insight.id,
                )
                items_processed += 1
                send_single_alert.delay(str(alert.id))

            # Update agent run
            agent_run.status = "success"
            agent_run.items_processed = items_processed
            agent_run.completed_at = datetime.now(timezone.utc)
            agent_run.duration_seconds = (
                agent_run.completed_at - started_at
            ).total_seconds()

            await db.commit()

        except Exception as exc:
            logger.exception("Error in alert processing")
            if agent_run:
                agent_run.status = "failed"
                agent_run.error_message = str(exc)[:1000]
                agent_run.completed_at = datetime.now(timezone.utc)
                agent_run.duration_seconds = (
                    agent_run.completed_at - started_at
                ).total_seconds()
                await db.commit()


async def _deliver_alert(alert_id: uuid.UUID):
    """Deliver an alert via Slack and Email."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        alert = result.scalar_one_or_none()
        if not alert:
            logger.warning("Alert %s not found for delivery", alert_id)
            return

        # Get workspace integrations
        int_result = await db.execute(
            select(Integration).where(
                Integration.user_id.isnot(None),  # placeholder for workspace integration lookup
                Integration.is_active.is_(True),
            )
        )

        delivery_channels = []

        # Deliver via Slack
        try:
            from ..services.slack_service import slack_service

            if settings.slack_bot_token:
                # Send to default alert channel
                await slack_service.send_alert_notification(
                    title=alert.title,
                    summary=alert.summary or "",
                    severity=alert.severity,
                    alert_url=f"{settings.frontend_url}/alerts",
                )
                delivery_channels.append("slack")
        except Exception:
            logger.exception("Failed to deliver alert %s via Slack", alert_id)

        # Deliver via Email
        try:
            from ..services.email_service import EmailService

            if settings.resend_api_key:
                await EmailService.send_alert_email(
                    title=alert.title,
                    summary=alert.summary or "",
                    severity=alert.severity,
                )
                delivery_channels.append("email")
        except Exception:
            logger.exception("Failed to deliver alert %s via Email", alert_id)

        alert.delivered_via = delivery_channels
        alert.delivered_at = datetime.now(timezone.utc)
        await db.commit()

        logger.info(
            "Delivered alert %s via %s", alert_id, delivery_channels
        )
