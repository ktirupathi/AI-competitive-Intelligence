"""Tests for the web monitor agent."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.web_monitor_agent import (
    _content_hash,
    _scrape_with_firecrawl,
    _scrape_with_httpx,
    scrape_url,
    web_monitor_agent,
)


class TestContentHash:
    """Tests for SHA-256 content hashing."""

    def test_identical_content_same_hash(self) -> None:
        assert _content_hash("hello world") == _content_hash("hello world")

    def test_normalises_whitespace(self) -> None:
        assert _content_hash("hello   world") == _content_hash("hello world")

    def test_normalises_case(self) -> None:
        assert _content_hash("Hello World") == _content_hash("hello world")

    def test_strips_leading_trailing(self) -> None:
        assert _content_hash("  hello  ") == _content_hash("hello")

    def test_different_content_different_hash(self) -> None:
        assert _content_hash("hello") != _content_hash("world")

    def test_returns_hex_digest(self) -> None:
        result = _content_hash("test")
        assert len(result) == 64  # SHA-256 hex digest length
        assert all(c in "0123456789abcdef" for c in result)


class TestScraping:
    """Tests for URL scraping functions."""

    @pytest.mark.asyncio
    async def test_scrape_with_firecrawl_success(
        self, mock_firecrawl_response: dict
    ) -> None:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_firecrawl_response
        mock_resp.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("agents.web_monitor_agent.settings") as mock_settings:
            mock_settings.firecrawl.api_key = "test-key"
            mock_settings.firecrawl.base_url = "https://api.firecrawl.dev/v1"
            mock_settings.firecrawl.timeout = 30

            result = await _scrape_with_firecrawl("https://acme.com", mock_client)

        assert result["content"] == "# Welcome to Acme Corp\n\nWe build enterprise software."
        assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_scrape_with_httpx_success(self) -> None:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.text = "<html><body>Hello</body></html>"
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        result = await _scrape_with_httpx("https://acme.com", mock_client)

        assert result["content"] == "<html><body>Hello</body></html>"
        assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_scrape_url_prefers_firecrawl(
        self, mock_firecrawl_response: dict
    ) -> None:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_firecrawl_response
        mock_resp.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("agents.web_monitor_agent.settings") as mock_settings:
            mock_settings.firecrawl.api_key = "test-key"
            mock_settings.firecrawl.base_url = "https://api.firecrawl.dev/v1"
            mock_settings.firecrawl.timeout = 30

            result = await scrape_url("https://acme.com", mock_client)

        assert "Acme Corp" in result["content"]

    @pytest.mark.asyncio
    async def test_scrape_url_falls_back_to_httpx(self) -> None:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.text = "Fallback content"
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("agents.web_monitor_agent.settings") as mock_settings:
            mock_settings.firecrawl.api_key = ""  # No key = no Firecrawl

            result = await scrape_url("https://acme.com", mock_client)

        assert result["content"] == "Fallback content"


class TestWebMonitorAgent:
    """Tests for the main web_monitor_agent function."""

    @pytest.mark.asyncio
    async def test_detects_no_changes_when_hash_matches(
        self, sample_competitor: dict
    ) -> None:
        content = "Same content as before"
        h = _content_hash(content)

        state = {
            "competitors": [sample_competitor],
            "previous_snapshots": [
                {
                    "url": "https://acme.com",
                    "content_hash": h,
                    "content_text": content,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "status_code": 200,
                }
            ],
            "errors": [],
        }

        mock_scrape_result = {"content": content, "status_code": 200}

        with (
            patch("agents.web_monitor_agent.scrape_url", new_callable=AsyncMock) as mock_scrape,
            patch("agents.web_monitor_agent.settings") as mock_settings,
        ):
            mock_scrape.return_value = mock_scrape_result
            mock_settings.pipeline.max_concurrent_competitors = 5
            mock_settings.pipeline.min_change_significance = 0.3
            mock_settings.firecrawl.api_key = ""

            result = await web_monitor_agent(state)

        assert len(result.get("changes", [])) == 0
        assert len(result.get("snapshots", [])) > 0

    @pytest.mark.asyncio
    async def test_detects_change_when_hash_differs(
        self, sample_competitor: dict
    ) -> None:
        old_content = "Old content"
        new_content = "New content that is different"

        state = {
            "competitors": [sample_competitor],
            "previous_snapshots": [
                {
                    "url": "https://acme.com",
                    "content_hash": _content_hash(old_content),
                    "content_text": old_content,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "status_code": 200,
                }
            ],
            "errors": [],
        }

        classification_response = {
            "diff_summary": "Content was significantly updated",
            "significance": "high",
            "change_category": "messaging",
            "reasoning": "Major copy change",
        }

        mock_claude_response = MagicMock()
        mock_claude_response.content = [
            MagicMock(text=json.dumps(classification_response))
        ]

        with (
            patch("agents.web_monitor_agent.scrape_url", new_callable=AsyncMock) as mock_scrape,
            patch("agents.web_monitor_agent.settings") as mock_settings,
            patch("agents.web_monitor_agent.anthropic") as mock_anthropic_mod,
        ):
            mock_scrape.return_value = {"content": new_content, "status_code": 200}
            mock_settings.pipeline.max_concurrent_competitors = 5
            mock_settings.pipeline.min_change_significance = 0.3
            mock_settings.anthropic.api_key = "test-key"
            mock_settings.anthropic.classification_model = "claude-haiku-4-5-20251001"
            mock_settings.anthropic.max_tokens_classification = 2048
            mock_settings.anthropic.temperature_classification = 0.1
            mock_settings.firecrawl.api_key = ""

            mock_client_instance = AsyncMock()
            mock_client_instance.messages.create = AsyncMock(
                return_value=mock_claude_response
            )
            mock_anthropic_mod.AsyncAnthropic.return_value = mock_client_instance

            result = await web_monitor_agent(state)

        changes = result.get("changes", [])
        assert len(changes) >= 1
        assert changes[0]["significance"] == "high"

    @pytest.mark.asyncio
    async def test_handles_scrape_failure_gracefully(
        self, sample_competitor: dict
    ) -> None:
        state = {
            "competitors": [sample_competitor],
            "previous_snapshots": [],
            "errors": [],
        }

        with (
            patch("agents.web_monitor_agent.scrape_url", new_callable=AsyncMock) as mock_scrape,
            patch("agents.web_monitor_agent.settings") as mock_settings,
        ):
            mock_scrape.side_effect = Exception("Connection timeout")
            mock_settings.pipeline.max_concurrent_competitors = 5
            mock_settings.pipeline.min_change_significance = 0.3
            mock_settings.firecrawl.api_key = ""

            result = await web_monitor_agent(state)

        assert len(result.get("errors", [])) > 0
        assert result.get("snapshots") is not None

    @pytest.mark.asyncio
    async def test_classification_prompt_formatting(self) -> None:
        """Verify the classification prompt is formatted correctly."""
        from agents.prompts import CHANGE_CLASSIFICATION_USER

        formatted = CHANGE_CLASSIFICATION_USER.format(
            competitor_name="Acme Corp",
            url="https://acme.com/pricing",
            previous_content="Old pricing: $99/month",
            current_content="New pricing: $149/month",
        )
        assert "Acme Corp" in formatted
        assert "https://acme.com/pricing" in formatted
        assert "$99/month" in formatted
        assert "$149/month" in formatted
