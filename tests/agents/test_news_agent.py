"""Tests for the news agent."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.news_agent import _search_serper, news_agent


class TestSerperSearch:
    """Tests for Serper API search."""

    @pytest.mark.asyncio
    async def test_search_serper_returns_organic_results(
        self, mock_serper_response: dict
    ) -> None:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_serper_response
        mock_resp.raise_for_status = MagicMock()
        mock_resp.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("agents.news_agent.settings") as mock_settings:
            mock_settings.web_search.api_key = "test-key"
            mock_settings.web_search.serper_base_url = "https://google.serper.dev"

            results = await _search_serper("Acme Corp news", mock_client)

        assert len(results) == 2
        assert results[0]["title"] == "Acme Corp raises $50M"
        assert results[0]["url"] == "https://techcrunch.com/acme-funding"

    @pytest.mark.asyncio
    async def test_search_serper_includes_news_results(self) -> None:
        response_with_news = {
            "organic": [],
            "news": [
                {
                    "title": "Breaking: Acme acquires startup",
                    "link": "https://example.com/news",
                    "snippet": "Acme Corp has acquired...",
                    "source": "Reuters",
                    "date": "2025-12-01",
                }
            ],
        }

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = response_with_news
        mock_resp.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("agents.news_agent.settings") as mock_settings:
            mock_settings.web_search.api_key = "test-key"
            mock_settings.web_search.serper_base_url = "https://google.serper.dev"

            results = await _search_serper("Acme Corp", mock_client)

        assert len(results) == 1
        assert results[0]["source"] == "Reuters"

    @pytest.mark.asyncio
    async def test_search_serper_empty_results(self) -> None:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"organic": [], "news": []}
        mock_resp.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("agents.news_agent.settings") as mock_settings:
            mock_settings.web_search.api_key = "test-key"
            mock_settings.web_search.serper_base_url = "https://google.serper.dev"

            results = await _search_serper("obscure query", mock_client)

        assert results == []


class TestNewsAgent:
    """Tests for the main news_agent function."""

    @pytest.mark.asyncio
    async def test_collects_news_for_competitors(
        self, sample_competitor: dict, mock_serper_response: dict
    ) -> None:
        state: dict[str, Any] = {
            "competitors": [sample_competitor],
            "errors": [],
        }

        analysis_response = {
            "summary": "Acme raised significant funding",
            "relevance_score": 0.9,
            "sentiment": "positive",
            "key_topics": ["funding"],
        }

        mock_claude_response = MagicMock()
        mock_claude_response.content = [
            MagicMock(text=json.dumps(analysis_response))
        ]

        with (
            patch("agents.news_agent.httpx.AsyncClient") as mock_http_cls,
            patch("agents.news_agent.settings") as mock_settings,
            patch("agents.news_agent.anthropic") as mock_anthropic_mod,
        ):
            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_serper_response
            mock_resp.raise_for_status = MagicMock()
            mock_http.post = AsyncMock(return_value=mock_resp)

            mock_settings.web_search.provider = "serper"
            mock_settings.web_search.api_key = "test-key"
            mock_settings.web_search.serper_base_url = "https://google.serper.dev"
            mock_settings.web_search.max_results = 10
            mock_settings.pipeline.max_concurrent_competitors = 5
            mock_settings.anthropic.api_key = "test-key"
            mock_settings.anthropic.classification_model = "claude-haiku-4-5-20251001"
            mock_settings.anthropic.max_tokens_classification = 2048
            mock_settings.anthropic.temperature_classification = 0.1

            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_claude_response)
            mock_anthropic_mod.AsyncAnthropic.return_value = mock_client

            result = await news_agent(state)

        assert len(result.get("news_items", [])) > 0
        assert result["news_items"][0]["relevance_score"] == 0.9

    @pytest.mark.asyncio
    async def test_handles_empty_competitors(self) -> None:
        state: dict[str, Any] = {
            "competitors": [],
            "errors": [],
        }

        with (
            patch("agents.news_agent.httpx.AsyncClient") as mock_http_cls,
            patch("agents.news_agent.settings") as mock_settings,
        ):
            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_settings.pipeline.max_concurrent_competitors = 5

            result = await news_agent(state)

        assert result.get("news_items", []) == []

    @pytest.mark.asyncio
    async def test_relevance_score_sorting(
        self, sample_competitor: dict
    ) -> None:
        """News items should be sorted by relevance_score descending."""
        state: dict[str, Any] = {
            "competitors": [sample_competitor],
            "errors": [],
        }

        responses = [
            {"summary": "Low relevance", "relevance_score": 0.2, "sentiment": "neutral", "key_topics": []},
            {"summary": "High relevance", "relevance_score": 0.95, "sentiment": "positive", "key_topics": []},
        ]
        call_count = 0

        async def mock_create(**kwargs: Any) -> MagicMock:
            nonlocal call_count
            idx = call_count % len(responses)
            call_count += 1
            resp = MagicMock()
            resp.content = [MagicMock(text=json.dumps(responses[idx]))]
            return resp

        serper_resp = {
            "organic": [
                {"title": "Article 1", "link": "https://a.com/1", "snippet": "s1", "source": "S1", "date": None},
                {"title": "Article 2", "link": "https://a.com/2", "snippet": "s2", "source": "S2", "date": None},
            ],
            "news": [],
        }

        with (
            patch("agents.news_agent.httpx.AsyncClient") as mock_http_cls,
            patch("agents.news_agent.settings") as mock_settings,
            patch("agents.news_agent.anthropic") as mock_anthropic_mod,
        ):
            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.json.return_value = serper_resp
            mock_resp.raise_for_status = MagicMock()
            mock_http.post = AsyncMock(return_value=mock_resp)

            mock_settings.web_search.provider = "serper"
            mock_settings.web_search.api_key = "test-key"
            mock_settings.web_search.serper_base_url = "https://google.serper.dev"
            mock_settings.web_search.max_results = 10
            mock_settings.pipeline.max_concurrent_competitors = 5
            mock_settings.anthropic.api_key = "test-key"
            mock_settings.anthropic.classification_model = "claude-haiku-4-5-20251001"
            mock_settings.anthropic.max_tokens_classification = 2048
            mock_settings.anthropic.temperature_classification = 0.1

            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(side_effect=mock_create)
            mock_anthropic_mod.AsyncAnthropic.return_value = mock_client

            result = await news_agent(state)

        items = result.get("news_items", [])
        if len(items) >= 2:
            assert items[0]["relevance_score"] >= items[1]["relevance_score"]
