"""Tests for the delivery agent."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.delivery_agent import (
    _briefing_to_html,
    _deliver_email,
    _deliver_slack,
    _deliver_webhook,
    delivery_agent,
)


class TestEmailDelivery:
    """Tests for email delivery via Resend."""

    @pytest.mark.asyncio
    async def test_skips_when_no_api_key(self, sample_briefing: dict) -> None:
        with patch("agents.delivery_agent.settings") as mock_settings:
            mock_settings.resend.api_key = ""
            result = await _deliver_email(sample_briefing, "test@example.com")

        assert result["success"] is False
        assert "not configured" in result["message"]

    @pytest.mark.asyncio
    async def test_sends_email_successfully(self, sample_briefing: dict) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "email-123"}
        mock_resp.raise_for_status = MagicMock()

        with (
            patch("agents.delivery_agent.settings") as mock_settings,
            patch("agents.delivery_agent.httpx.AsyncClient") as mock_http_cls,
        ):
            mock_settings.resend.api_key = "re_test_key"
            mock_settings.resend.from_address = "test@scoutai.app"

            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(return_value=mock_resp)

            result = await _deliver_email(sample_briefing, "user@example.com")

        assert result["success"] is True
        assert result["channel"] == "email"

    @pytest.mark.asyncio
    async def test_handles_email_failure(self, sample_briefing: dict) -> None:
        with (
            patch("agents.delivery_agent.settings") as mock_settings,
            patch("agents.delivery_agent.httpx.AsyncClient") as mock_http_cls,
        ):
            mock_settings.resend.api_key = "re_test_key"
            mock_settings.resend.from_address = "test@scoutai.app"

            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(side_effect=Exception("Connection refused"))

            result = await _deliver_email(sample_briefing, "user@example.com")

        assert result["success"] is False


class TestSlackDelivery:
    """Tests for Slack delivery."""

    @pytest.mark.asyncio
    async def test_skips_when_no_token(self, sample_briefing: dict) -> None:
        with patch("agents.delivery_agent.settings") as mock_settings:
            mock_settings.slack.bot_token = ""
            result = await _deliver_slack(sample_briefing, "#test")

        assert result["success"] is False
        assert "not configured" in result["message"]

    @pytest.mark.asyncio
    async def test_posts_to_slack_successfully(self, sample_briefing: dict) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "ts": "1234567890.123456"}

        with (
            patch("agents.delivery_agent.settings") as mock_settings,
            patch("agents.delivery_agent.httpx.AsyncClient") as mock_http_cls,
        ):
            mock_settings.slack.bot_token = "xoxb-test-token"

            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(return_value=mock_resp)

            result = await _deliver_slack(sample_briefing, "#competitive-intel")

        assert result["success"] is True
        assert result["channel"] == "slack"

    @pytest.mark.asyncio
    async def test_handles_slack_api_error(self, sample_briefing: dict) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": False, "error": "channel_not_found"}

        with (
            patch("agents.delivery_agent.settings") as mock_settings,
            patch("agents.delivery_agent.httpx.AsyncClient") as mock_http_cls,
        ):
            mock_settings.slack.bot_token = "xoxb-test-token"

            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(return_value=mock_resp)

            result = await _deliver_slack(sample_briefing, "#nonexistent")

        assert result["success"] is False


class TestWebhookDelivery:
    """Tests for webhook delivery."""

    @pytest.mark.asyncio
    async def test_skips_when_no_url(self, sample_briefing: dict) -> None:
        result = await _deliver_webhook(sample_briefing, "")
        assert result["success"] is False
        assert "not configured" in result["message"]

    @pytest.mark.asyncio
    async def test_delivers_to_webhook(self, sample_briefing: dict) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        with (
            patch("agents.delivery_agent.settings") as mock_settings,
            patch("agents.delivery_agent.httpx.AsyncClient") as mock_http_cls,
        ):
            mock_settings.webhook.secret = None

            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(return_value=mock_resp)

            result = await _deliver_webhook(sample_briefing, "https://hooks.example.com/test")

        assert result["success"] is True
        assert result["channel"] == "webhook"

    @pytest.mark.asyncio
    async def test_includes_signature_when_secret_set(
        self, sample_briefing: dict
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        with (
            patch("agents.delivery_agent.settings") as mock_settings,
            patch("agents.delivery_agent.httpx.AsyncClient") as mock_http_cls,
        ):
            mock_settings.webhook.secret = "test-secret"

            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(return_value=mock_resp)

            result = await _deliver_webhook(sample_briefing, "https://hooks.example.com/test")

        assert result["success"] is True
        # Verify the post was called with signature header
        call_kwargs = mock_http.post.call_args
        headers = call_kwargs.kwargs.get("headers", {})
        assert "X-Scout-Signature" in headers


class TestBriefingToHtml:
    """Tests for HTML email generation."""

    def test_generates_valid_html(self, sample_briefing: dict) -> None:
        html = _briefing_to_html(sample_briefing)
        assert "<html>" in html
        assert "Executive Summary" in html
        assert "Acme Corp" in html
        assert "Scout AI" in html

    def test_handles_empty_briefing(self) -> None:
        from agents.synthesis_agent import _empty_briefing
        html = _briefing_to_html(_empty_briefing())
        assert "<html>" in html


class TestDeliveryAgent:
    """Tests for the main delivery_agent function."""

    @pytest.mark.asyncio
    async def test_skips_delivery_when_no_briefing(self) -> None:
        state: dict[str, Any] = {
            "briefing": None,
            "user_email": "test@example.com",
            "errors": [],
        }

        result = await delivery_agent(state)

        assert result.get("delivery_results", []) == []

    @pytest.mark.asyncio
    async def test_delivers_to_all_channels(
        self, sample_pipeline_state: dict, sample_briefing: dict
    ) -> None:
        sample_pipeline_state["briefing"] = sample_briefing

        with (
            patch("agents.delivery_agent._deliver_email", new_callable=AsyncMock) as mock_email,
            patch("agents.delivery_agent._deliver_slack", new_callable=AsyncMock) as mock_slack,
            patch("agents.delivery_agent._deliver_webhook", new_callable=AsyncMock) as mock_webhook,
            patch("agents.delivery_agent.settings") as mock_settings,
        ):
            mock_settings.slack.bot_token = "xoxb-test"
            mock_settings.slack.default_channel = "#test"
            mock_settings.webhook.url = None

            mock_email.return_value = {
                "channel": "email", "success": True,
                "message": "Sent", "delivered_at": "now",
            }
            mock_slack.return_value = {
                "channel": "slack", "success": True,
                "message": "Posted", "delivered_at": "now",
            }
            mock_webhook.return_value = {
                "channel": "webhook", "success": True,
                "message": "Delivered", "delivered_at": "now",
            }

            result = await delivery_agent(sample_pipeline_state)

        results = result.get("delivery_results", [])
        assert len(results) >= 2  # email + slack at minimum
        assert all(r["success"] for r in results)
