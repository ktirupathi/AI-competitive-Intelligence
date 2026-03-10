"""Scheduled briefing generation tasks."""

import asyncio
import logging
import uuid

from sqlalchemy import select

from ..celery_app import celery
from ..config import get_settings
from ..database import async_session_factory
from ..models.integration import Integration
from ..models.user import User
from ..services.briefing_service import BriefingService
from ..services.email_service import EmailService
from ..services.slack_service import slack_service

logger = logging.getLogger(__name__)
settings = get_settings()


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery.task(name="apps.api.tasks.briefing_generation.generate_all_briefings")
def generate_all_briefings():
    """Generate briefings for all active users based on their frequency preferences."""
    logger.info("Starting scheduled briefing generation")
    _run_async(_generate_all())
    logger.info("Briefing generation complete")


@celery.task(name="apps.api.tasks.briefing_generation.generate_user_briefing")
def generate_user_briefing(user_id: str, frequency: str = "weekly"):
    """Generate a briefing for a specific user."""
    _run_async(_generate_for_user(uuid.UUID(user_id), frequency))


async def _generate_all():
    """Generate briefings for all eligible users."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(User).where(
                User.is_active.is_(True),
                User.plan != "free",  # Only paid users get scheduled briefings
            )
        )
        users = list(result.scalars().all())

    logger.info("Generating briefings for %d users", len(users))

    for user in users:
        try:
            await _generate_for_user(user.id, user.briefing_frequency)
        except Exception:
            logger.exception(
                "Error generating briefing for user %s", user.id
            )


async def _generate_for_user(user_id: uuid.UUID, frequency: str):
    """Generate and deliver a briefing for a single user."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            logger.warning("User %s not found", user_id)
            return

        if not user.is_active:
            return

        # Generate the briefing
        service = BriefingService(db)
        try:
            briefing = await service.generate_briefing(
                user=user,
                frequency=frequency,
            )
        except ValueError as exc:
            logger.info("Skipping briefing for user %s: %s", user_id, exc)
            return

        # Deliver via configured channels
        await _deliver_briefing(db, user, briefing)

        # Update briefing status
        briefing.status = "sent"
        from datetime import datetime, timezone
        briefing.sent_at = datetime.now(timezone.utc)
        delivery_channels = []

        await db.commit()
        logger.info(
            "Briefing %s generated and delivered for user %s",
            briefing.id,
            user.id,
        )


async def _deliver_briefing(db, user: User, briefing):
    """Deliver a briefing through all configured integrations."""
    result = await db.execute(
        select(Integration).where(
            Integration.user_id == user.id,
            Integration.is_active.is_(True),
        )
    )
    integrations = list(result.scalars().all())

    briefing_url = f"{settings.frontend_url}/briefings/{briefing.id}"
    delivery_channels = []

    for integration in integrations:
        try:
            if integration.type == "email":
                await EmailService.send_briefing_email(
                    to=integration.email_address or user.email,
                    briefing_title=briefing.title,
                    executive_summary=briefing.executive_summary or "",
                    full_content_html=_markdown_to_html(briefing.full_content or ""),
                    briefing_url=briefing_url,
                )
                delivery_channels.append("email")

            elif integration.type == "slack":
                await slack_service.send_briefing_notification(
                    channel=integration.slack_channel_id,
                    briefing_title=briefing.title,
                    executive_summary=briefing.executive_summary or "",
                    competitor_count=briefing.competitor_count,
                    insight_count=briefing.insight_count,
                    change_count=briefing.change_count,
                    briefing_url=briefing_url,
                    token=integration.slack_access_token,
                )
                delivery_channels.append("slack")

            elif integration.type == "webhook":
                import httpx
                async with httpx.AsyncClient() as client:
                    await client.post(
                        integration.webhook_url,
                        json={
                            "event": "briefing.generated",
                            "briefing_id": str(briefing.id),
                            "title": briefing.title,
                            "executive_summary": briefing.executive_summary,
                            "url": briefing_url,
                            "competitor_count": briefing.competitor_count,
                            "insight_count": briefing.insight_count,
                            "change_count": briefing.change_count,
                        },
                        headers={
                            "X-Scout-Signature": integration.webhook_secret or "",
                            "Content-Type": "application/json",
                        },
                        timeout=10.0,
                    )
                delivery_channels.append("webhook")

        except Exception:
            logger.exception(
                "Error delivering briefing via %s for user %s",
                integration.type,
                user.id,
            )

    briefing.delivery_channels = delivery_channels

    # Also send to user's primary email if no email integration is configured
    if "email" not in delivery_channels:
        notification_prefs = user.notification_prefs or {}
        if notification_prefs.get("briefing_delivery", True):
            try:
                await EmailService.send_briefing_email(
                    to=user.email,
                    briefing_title=briefing.title,
                    executive_summary=briefing.executive_summary or "",
                    full_content_html=_markdown_to_html(briefing.full_content or ""),
                    briefing_url=briefing_url,
                )
                delivery_channels.append("email_primary")
            except Exception:
                logger.exception(
                    "Error sending primary email briefing for user %s", user.id
                )


def _markdown_to_html(markdown_text: str) -> str:
    """Simple markdown to HTML conversion for emails."""
    import re

    html = markdown_text
    # Headers
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    # Bold and italic
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
    # Lists
    html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    # Paragraphs (double newlines)
    html = re.sub(r"\n\n", "</p><p>", html)
    html = f"<p>{html}</p>"
    return html
