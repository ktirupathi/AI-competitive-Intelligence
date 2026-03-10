"""Email service using Resend."""

import logging
from typing import Any

import resend

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

resend.api_key = settings.resend_api_key


class EmailService:
    """Send transactional emails via Resend."""

    @staticmethod
    async def send_email(
        to: str | list[str],
        subject: str,
        html: str,
        text: str | None = None,
        reply_to: str | None = None,
        tags: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Send a single email."""
        params: dict[str, Any] = {
            "from_": settings.email_from,
            "to": to if isinstance(to, list) else [to],
            "subject": subject,
            "html": html,
        }
        if text:
            params["text"] = text
        if reply_to:
            params["reply_to"] = reply_to
        if tags:
            params["tags"] = tags

        try:
            result = resend.Emails.send(params)
            logger.info("Email sent to %s: subject=%s", to, subject)
            return result
        except Exception:
            logger.exception("Failed to send email to %s", to)
            raise

    @staticmethod
    async def send_briefing_email(
        to: str,
        briefing_title: str,
        executive_summary: str,
        full_content_html: str,
        briefing_url: str,
    ) -> dict[str, Any]:
        """Send a briefing email with formatted content."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                      max-width: 600px; margin: 0 auto; padding: 20px; color: #1a1a1a;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #6366f1; margin: 0;">Scout AI</h1>
                <p style="color: #6b7280; margin-top: 4px;">Competitive Intelligence Briefing</p>
            </div>

            <h2 style="font-size: 20px; margin-bottom: 16px;">{briefing_title}</h2>

            <div style="background: #f3f4f6; border-radius: 8px; padding: 16px; margin-bottom: 24px;">
                <h3 style="margin-top: 0; color: #4f46e5;">Executive Summary</h3>
                <p>{executive_summary}</p>
            </div>

            <div style="margin-bottom: 24px;">
                {full_content_html}
            </div>

            <div style="text-align: center; margin-top: 32px;">
                <a href="{briefing_url}"
                   style="background: #6366f1; color: white; padding: 12px 24px;
                          border-radius: 6px; text-decoration: none; font-weight: 600;">
                    View Full Briefing
                </a>
            </div>

            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 32px 0;">
            <p style="color: #9ca3af; font-size: 12px; text-align: center;">
                You received this email because you have briefing delivery enabled in Scout AI.
                <br>Manage your preferences in Settings.
            </p>
        </body>
        </html>
        """

        return await EmailService.send_email(
            to=to,
            subject=f"Scout AI: {briefing_title}",
            html=html,
            tags=[{"name": "type", "value": "briefing"}],
        )

    @staticmethod
    async def send_alert_email(
        to: str,
        competitor_name: str,
        alert_title: str,
        alert_summary: str,
        severity: str,
        dashboard_url: str,
    ) -> dict[str, Any]:
        """Send a real-time alert email."""
        severity_colors = {
            "low": "#22c55e",
            "medium": "#eab308",
            "high": "#f97316",
            "critical": "#ef4444",
        }
        color = severity_colors.get(severity, "#6b7280")

        html = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                      max-width: 600px; margin: 0 auto; padding: 20px; color: #1a1a1a;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="color: #6366f1; margin: 0; font-size: 18px;">Scout AI Alert</h1>
            </div>

            <div style="border-left: 4px solid {color}; padding: 16px; background: #f9fafb;
                        border-radius: 0 8px 8px 0; margin-bottom: 20px;">
                <p style="margin: 0 0 4px 0; font-size: 12px; text-transform: uppercase;
                          font-weight: 600; color: {color};">{severity} priority</p>
                <h2 style="margin: 0 0 8px 0; font-size: 18px;">{alert_title}</h2>
                <p style="margin: 0; color: #6b7280; font-size: 14px;">Competitor: {competitor_name}</p>
            </div>

            <p>{alert_summary}</p>

            <div style="text-align: center; margin-top: 24px;">
                <a href="{dashboard_url}"
                   style="background: #6366f1; color: white; padding: 10px 20px;
                          border-radius: 6px; text-decoration: none; font-weight: 500;">
                    View Details
                </a>
            </div>
        </body>
        </html>
        """

        return await EmailService.send_email(
            to=to,
            subject=f"[{severity.upper()}] {competitor_name}: {alert_title}",
            html=html,
            tags=[
                {"name": "type", "value": "alert"},
                {"name": "severity", "value": severity},
            ],
        )
