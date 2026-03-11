"""Tests for the social media agent."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.social_agent import (
    _extract_metric,
    _parse_linkedin_markdown,
    _parse_twitter_markdown,
    social_agent,
)


class TestExtractMetric:
    """Tests for engagement metric extraction."""

    def test_extracts_likes(self) -> None:
        assert _extract_metric("150 likes", r"(\d[\d,]*)\s*(?:like|reaction)", 0) == 150

    def test_extracts_with_commas(self) -> None:
        assert _extract_metric("1,234 likes", r"(\d[\d,]*)\s*(?:like|reaction)", 0) == 1234

    def test_returns_default_when_no_match(self) -> None:
        assert _extract_metric("no numbers here", r"(\d[\d,]*)\s*like", 0) == 0

    def test_case_insensitive(self) -> None:
        assert _extract_metric("150 LIKES", r"(\d[\d,]*)\s*(?:like|reaction)", 0) == 150


class TestParseLinkedIn:
    """Tests for LinkedIn post parsing."""

    def test_parses_post_blocks(self) -> None:
        content = """
---
We're excited to announce our new product! This is a game-changing feature.
150 likes 25 comments 10 reposts

---
Join our team! We're hiring across all departments.
50 likes 5 comments
"""
        posts = _parse_linkedin_markdown(content, "https://linkedin.com/company/acme")
        assert len(posts) == 2
        assert posts[0]["likes"] == 150
        assert posts[0]["platform"] == "linkedin"

    def test_skips_short_blocks(self) -> None:
        content = "---\nShort\n---"
        posts = _parse_linkedin_markdown(content, "https://linkedin.com/company/acme")
        assert len(posts) == 0

    def test_caps_at_20_posts(self) -> None:
        blocks = []
        for i in range(25):
            blocks.append(
                f"---\nThis is post number {i} with enough content to be parsed correctly "
                f"and pass the minimum length check.\n"
            )
        content = "\n".join(blocks)
        posts = _parse_linkedin_markdown(content, "https://linkedin.com/company/acme")
        assert len(posts) <= 20


class TestParseTwitter:
    """Tests for Twitter/X post parsing."""

    def test_parses_tweet_blocks(self) -> None:
        content = """
---
Excited to share our latest quarterly results! Revenue up 40% YoY.
200 likes 50 replies 30 retweets

---
"""
        posts = _parse_twitter_markdown(content, "acme")
        assert len(posts) == 1
        assert posts[0]["likes"] == 200
        assert posts[0]["shares"] == 30
        assert posts[0]["platform"] == "twitter"


class TestPostClassification:
    """Tests for social post classification."""

    @pytest.mark.asyncio
    async def test_classifies_product_launch(self) -> None:
        from agents.social_agent import _classify_post

        classification = {
            "post_type": "product_launch",
            "summary": "Announcing new AI-powered feature",
            "engagement_score": 0.85,
            "strategic_relevance": "high",
            "key_topics": ["AI", "product"],
        }

        mock_claude_response = MagicMock()
        mock_claude_response.content = [
            MagicMock(text=json.dumps(classification))
        ]

        with (
            patch("agents.social_agent.settings") as mock_settings,
            patch("agents.social_agent.anthropic") as mock_anthropic_mod,
        ):
            mock_settings.anthropic.api_key = "test-key"
            mock_settings.anthropic.classification_model = "claude-haiku-4-5-20251001"
            mock_settings.anthropic.max_tokens_classification = 2048
            mock_settings.anthropic.temperature_classification = 0.1

            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_claude_response)
            mock_anthropic_mod.AsyncAnthropic.return_value = mock_client

            result = await _classify_post(
                "Acme", "linkedin", "Acme Corp",
                "Excited to launch our new AI feature!", 100, 20, 15
            )

        assert result["post_type"] == "product_launch"
        assert result["engagement_score"] == 0.85


class TestSocialAgent:
    """Tests for the main social_agent function."""

    @pytest.mark.asyncio
    async def test_handles_no_social_urls(self) -> None:
        state: dict[str, Any] = {
            "competitors": [
                {
                    "name": "NoSocial Corp",
                    "domain": "nosocial.com",
                    "linkedin_url": None,
                    "twitter_handle": None,
                }
            ],
            "errors": [],
        }

        with (
            patch("agents.social_agent.httpx.AsyncClient") as mock_http_cls,
            patch("agents.social_agent.settings") as mock_settings,
        ):
            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_settings.pipeline.max_concurrent_competitors = 5

            result = await social_agent(state)

        assert result.get("social_posts", []) == []

    @pytest.mark.asyncio
    async def test_collects_linkedin_and_twitter(
        self, sample_competitor: dict
    ) -> None:
        state: dict[str, Any] = {
            "competitors": [sample_competitor],
            "errors": [],
        }

        linkedin_posts = [
            {
                "platform": "linkedin",
                "author": "Acme Corp",
                "content": "Excited to announce our new product launch with AI features!",
                "url": None,
                "posted_at": None,
                "likes": 100,
                "comments": 20,
                "shares": 10,
            }
        ]

        classification = {
            "post_type": "product_launch",
            "summary": "New product announcement",
            "engagement_score": 0.7,
            "strategic_relevance": "high",
            "key_topics": ["product"],
        }

        mock_claude_response = MagicMock()
        mock_claude_response.content = [
            MagicMock(text=json.dumps(classification))
        ]

        with (
            patch("agents.social_agent._scrape_linkedin_posts", new_callable=AsyncMock) as mock_li,
            patch("agents.social_agent._scrape_twitter_posts", new_callable=AsyncMock) as mock_tw,
            patch("agents.social_agent.httpx.AsyncClient") as mock_http_cls,
            patch("agents.social_agent.settings") as mock_settings,
            patch("agents.social_agent.anthropic") as mock_anthropic_mod,
        ):
            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_li.return_value = linkedin_posts
            mock_tw.return_value = []

            mock_settings.pipeline.max_concurrent_competitors = 5
            mock_settings.anthropic.api_key = "test-key"
            mock_settings.anthropic.classification_model = "claude-haiku-4-5-20251001"
            mock_settings.anthropic.max_tokens_classification = 2048
            mock_settings.anthropic.temperature_classification = 0.1

            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_claude_response)
            mock_anthropic_mod.AsyncAnthropic.return_value = mock_client

            result = await social_agent(state)

        posts = result.get("social_posts", [])
        assert len(posts) >= 1
        assert posts[0]["post_type"] == "product_launch"
