"""Tests for the review agent."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.review_agent import (
    _build_capterra_url,
    _build_g2_url,
    _extract_reviews_from_content,
    review_agent,
)


class TestURLBuilders:
    """Tests for review platform URL builders."""

    def test_g2_url(self) -> None:
        assert _build_g2_url("acme-corp") == "https://www.g2.com/products/acme-corp/reviews"

    def test_capterra_url(self) -> None:
        assert _build_capterra_url("12345/acme") == "https://www.capterra.com/p/12345/acme/reviews/"


class TestExtractReviews:
    """Tests for review extraction from scraped content."""

    def test_extracts_g2_reviews_with_ratings(self) -> None:
        content = """
---
Great product for enterprise

4.5/5 stars

This is an amazing product that helps our team collaborate better.
The integrations are fantastic.

---
Needs improvement

2.0/5 stars

The product crashes frequently and support is slow to respond.

---
"""
        reviews = _extract_reviews_from_content(content, "g2")
        assert len(reviews) >= 2
        assert reviews[0]["rating"] == 4.5

    def test_extracts_capterra_reviews(self) -> None:
        content = """
---
Best tool in the market
Overall: 5/5

Industry: Technology
Role: CTO

Amazing tool that transformed our workflow.

---
"""
        reviews = _extract_reviews_from_content(content, "capterra")
        assert len(reviews) >= 1
        assert reviews[0]["rating"] == 5.0

    def test_skips_short_blocks(self) -> None:
        content = "---\nShort\n---\nAlso short\n---"
        reviews = _extract_reviews_from_content(content, "g2")
        assert len(reviews) == 0

    def test_caps_at_30_reviews(self) -> None:
        blocks = []
        for i in range(40):
            blocks.append(
                f"---\nReview title number {i} is here for testing\n"
                f"4.0/5 stars\n"
                f"This is a sufficiently long review text to pass the minimum length requirement "
                f"for the extraction heuristic.\n"
            )
        content = "\n".join(blocks)
        reviews = _extract_reviews_from_content(content, "g2")
        assert len(reviews) <= 30


class TestSentimentScoring:
    """Tests for sentiment analysis of reviews."""

    @pytest.mark.asyncio
    async def test_positive_review_sentiment(self) -> None:
        from agents.review_agent import _analyse_review

        analysis_response = {
            "sentiment": "positive",
            "pros_summary": "Feature-rich and reliable",
            "cons_summary": "Slightly expensive",
            "key_themes": ["features", "pricing"],
            "competitive_relevance": "Strong competitor in enterprise space",
        }

        mock_claude_response = MagicMock()
        mock_claude_response.content = [
            MagicMock(text=json.dumps(analysis_response))
        ]

        with (
            patch("agents.review_agent.settings") as mock_settings,
            patch("agents.review_agent.anthropic") as mock_anthropic_mod,
        ):
            mock_settings.anthropic.api_key = "test-key"
            mock_settings.anthropic.classification_model = "claude-haiku-4-5-20251001"
            mock_settings.anthropic.max_tokens_classification = 2048
            mock_settings.anthropic.temperature_classification = 0.1

            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_claude_response)
            mock_anthropic_mod.AsyncAnthropic.return_value = mock_client

            result = await _analyse_review("Acme", "g2", 4.5, "Great product", "Love it!")

        assert result["sentiment"] == "positive"


class TestReviewAgent:
    """Tests for the main review_agent function."""

    @pytest.mark.asyncio
    async def test_skips_competitors_without_slugs(self) -> None:
        state: dict[str, Any] = {
            "competitors": [
                {
                    "name": "NoSlug Corp",
                    "domain": "noslug.com",
                    "g2_slug": None,
                    "capterra_slug": None,
                }
            ],
            "errors": [],
        }

        with (
            patch("agents.review_agent.httpx.AsyncClient") as mock_http_cls,
            patch("agents.review_agent.settings") as mock_settings,
        ):
            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_settings.pipeline.max_concurrent_competitors = 5

            result = await review_agent(state)

        assert result.get("reviews", []) == []

    @pytest.mark.asyncio
    async def test_collects_reviews_from_g2(
        self, sample_competitor: dict
    ) -> None:
        state: dict[str, Any] = {
            "competitors": [sample_competitor],
            "errors": [],
        }

        g2_content = """
---
Excellent enterprise tool with great support

4.5/5 stars

This product has been a game-changer for our competitive intelligence workflow.
The dashboards are intuitive and the alerts are timely.

---
"""
        analysis_response = {
            "sentiment": "positive",
            "pros_summary": "Intuitive dashboards, timely alerts",
            "cons_summary": "",
            "key_themes": ["dashboards", "alerts"],
            "competitive_relevance": "Strong competitor",
        }

        mock_claude_response = MagicMock()
        mock_claude_response.content = [
            MagicMock(text=json.dumps(analysis_response))
        ]

        with (
            patch("agents.review_agent._scrape_page", new_callable=AsyncMock) as mock_scrape,
            patch("agents.review_agent.httpx.AsyncClient") as mock_http_cls,
            patch("agents.review_agent.settings") as mock_settings,
            patch("agents.review_agent.anthropic") as mock_anthropic_mod,
        ):
            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_scrape.return_value = g2_content
            mock_settings.pipeline.max_concurrent_competitors = 5
            mock_settings.anthropic.api_key = "test-key"
            mock_settings.anthropic.classification_model = "claude-haiku-4-5-20251001"
            mock_settings.anthropic.max_tokens_classification = 2048
            mock_settings.anthropic.temperature_classification = 0.1
            mock_settings.firecrawl.api_key = ""

            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_claude_response)
            mock_anthropic_mod.AsyncAnthropic.return_value = mock_client

            result = await review_agent(state)

        reviews = result.get("reviews", [])
        assert len(reviews) >= 1
        assert reviews[0]["sentiment"] == "positive"
