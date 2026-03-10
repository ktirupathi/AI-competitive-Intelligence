"""Slack integration service."""

import logging
from typing import Any

from slack_bolt.async_app import AsyncApp

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SlackService:
    """Send notifications to Slack channels."""

    def __init__(self):
        self._app: AsyncApp | None = None

    @property
    def app(self) -> AsyncApp:
        if self._app is None:
            self._app = AsyncApp(
                token=settings.slack_bot_token,
                signing_secret=settings.slack_signing_secret,
            )
        return self._app

    async def send_message(
        self,
        channel: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
        token: str | None = None,
    ) -> dict:
        """Send a message to a Slack channel."""
        try:
            client = self.app.client
            if token:
                from slack_sdk.web.async_client import AsyncWebClient
                client = AsyncWebClient(token=token)

            response = await client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks,
            )
            logger.info("Slack message sent to %s", channel)
            return response.data
        except Exception:
            logger.exception("Failed to send Slack message to %s", channel)
            raise

    async def send_alert(
        self,
        channel: str,
        competitor_name: str,
        alert_title: str,
        alert_summary: str,
        severity: str,
        dashboard_url: str,
        token: str | None = None,
    ) -> dict:
        """Send a formatted alert to Slack."""
        severity_emoji = {
            "low": ":large_blue_circle:",
            "medium": ":large_yellow_circle:",
            "high": ":large_orange_circle:",
            "critical": ":red_circle:",
        }
        emoji = severity_emoji.get(severity, ":white_circle:")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Scout AI Alert",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Competitor:*\n{competitor_name}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{severity.upper()}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{alert_title}*\n{alert_summary}",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View in Scout AI",
                        },
                        "url": dashboard_url,
                        "style": "primary",
                    },
                ],
            },
        ]

        return await self.send_message(
            channel=channel,
            text=f"[{severity.upper()}] {competitor_name}: {alert_title}",
            blocks=blocks,
            token=token,
        )

    async def send_briefing_notification(
        self,
        channel: str,
        briefing_title: str,
        executive_summary: str,
        competitor_count: int,
        insight_count: int,
        change_count: int,
        briefing_url: str,
        token: str | None = None,
    ) -> dict:
        """Send a briefing notification to Slack."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":newspaper: Scout AI Briefing Ready",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{briefing_title}*",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Competitors:* {competitor_count}"},
                    {"type": "mrkdwn", "text": f"*Insights:* {insight_count}"},
                    {"type": "mrkdwn", "text": f"*Changes:* {change_count}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Summary:*\n{executive_summary[:500]}{'...' if len(executive_summary) > 500 else ''}",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Read Full Briefing"},
                        "url": briefing_url,
                        "style": "primary",
                    },
                ],
            },
        ]

        return await self.send_message(
            channel=channel,
            text=f"New briefing: {briefing_title}",
            blocks=blocks,
            token=token,
        )

    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> dict:
        """Exchange an OAuth code for an access token."""
        from slack_sdk.web.async_client import AsyncWebClient

        client = AsyncWebClient()
        response = await client.oauth_v2_access(
            client_id=settings.slack_client_id,
            client_secret=settings.slack_client_secret,
            code=code,
            redirect_uri=redirect_uri,
        )
        return response.data


# Module-level singleton
slack_service = SlackService()
