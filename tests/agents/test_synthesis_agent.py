"""Tests for the synthesis agent."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.synthesis_agent import (
    _clamp,
    _empty_briefing,
    _safe_json,
    _validate_and_normalise,
    synthesis_agent,
)


class TestHelpers:
    """Tests for synthesis helper functions."""

    def test_clamp_within_range(self) -> None:
        assert _clamp(0.5) == 0.5

    def test_clamp_below_min(self) -> None:
        assert _clamp(-0.5) == 0.0

    def test_clamp_above_max(self) -> None:
        assert _clamp(1.5) == 1.0

    def test_clamp_invalid_type(self) -> None:
        assert _clamp("invalid") == 0.5

    def test_safe_json_truncates(self) -> None:
        long_obj = {"data": "x" * 20000}
        result = _safe_json(long_obj, max_chars=100)
        assert len(result) <= 120  # 100 + truncation message
        assert "[truncated]" in result

    def test_safe_json_handles_unserializable(self) -> None:
        result = _safe_json(datetime.now())
        assert isinstance(result, str)

    def test_empty_briefing_has_all_fields(self) -> None:
        briefing = _empty_briefing()
        assert "executive_summary" in briefing
        assert "top_insights" in briefing
        assert "predictive_signals" in briefing
        assert "recommended_plays" in briefing
        assert "competitor_summaries" in briefing
        assert "generated_at" in briefing


class TestValidateAndNormalise:
    """Tests for briefing validation and normalisation."""

    def test_normalises_valid_briefing(self) -> None:
        raw = {
            "executive_summary": "Test summary",
            "top_insights": [
                {
                    "title": "Insight 1",
                    "description": "Description 1",
                    "impact_score": 0.8,
                    "confidence_score": 0.7,
                    "category": "strategy",
                    "sources": ["source1"],
                }
            ],
            "predictive_signals": [],
            "recommended_plays": [
                {
                    "action": "Do something",
                    "rationale": "Because reasons",
                    "priority": "high",
                    "effort": "medium",
                }
            ],
            "competitor_summaries": [
                {
                    "name": "Acme Corp",
                    "key_changes": ["change1"],
                    "threat_level": "high",
                }
            ],
        }
        competitors = [{"name": "Acme Corp", "domain": "acme.com"}]

        result = _validate_and_normalise(raw, competitors)

        assert result["executive_summary"] == "Test summary"
        assert len(result["top_insights"]) == 1
        assert result["top_insights"][0]["impact_score"] == 0.8
        assert result["competitor_summaries"][0]["threat_level"] == "high"

    def test_fills_defaults_for_missing_fields(self) -> None:
        raw: dict[str, Any] = {}
        competitors = [{"name": "Test", "domain": "test.com"}]

        result = _validate_and_normalise(raw, competitors)

        assert result["executive_summary"] == "No executive summary generated."
        assert result["top_insights"] == []
        assert len(result["competitor_summaries"]) == 1
        assert result["competitor_summaries"][0]["threat_level"] == "low"

    def test_clamps_scores(self) -> None:
        raw = {
            "top_insights": [
                {
                    "title": "Test",
                    "description": "test",
                    "impact_score": 5.0,  # Too high
                    "confidence_score": -1.0,  # Too low
                }
            ],
        }
        competitors: list[dict] = []

        result = _validate_and_normalise(raw, competitors)

        assert result["top_insights"][0]["impact_score"] == 1.0
        assert result["top_insights"][0]["confidence_score"] == 0.0

    def test_invalid_priority_defaults_to_medium(self) -> None:
        raw = {
            "recommended_plays": [
                {
                    "action": "Do something",
                    "rationale": "Because",
                    "priority": "ULTRA_HIGH",
                    "effort": "low",
                }
            ],
        }
        result = _validate_and_normalise(raw, [])
        assert result["recommended_plays"][0]["priority"] == "medium"


class TestSynthesisAgent:
    """Tests for the main synthesis_agent function."""

    @pytest.mark.asyncio
    async def test_returns_empty_briefing_on_no_signals(self) -> None:
        state: dict[str, Any] = {
            "competitors": [{"name": "Acme", "domain": "acme.com"}],
            "changes": [],
            "news_items": [],
            "job_postings": [],
            "reviews": [],
            "social_posts": [],
            "signal_clusters": [],
            "predictions": [],
            "errors": [],
        }

        result = await synthesis_agent(state)

        assert "No data was collected" in result["briefing"]["executive_summary"]
        assert result["insights"] == []

    @pytest.mark.asyncio
    async def test_generates_briefing_from_signals(
        self, sample_pipeline_state: dict
    ) -> None:
        briefing_response = {
            "executive_summary": "Acme Corp is expanding aggressively.",
            "top_insights": [
                {
                    "title": "ML Investment",
                    "description": "Hiring surge in ML roles",
                    "impact_score": 0.85,
                    "confidence_score": 0.8,
                    "category": "talent",
                    "sources": ["job_postings"],
                }
            ],
            "predictive_signals": [],
            "recommended_plays": [],
            "competitor_summaries": [
                {
                    "name": "Acme Corp",
                    "key_changes": ["ML hiring"],
                    "threat_level": "high",
                }
            ],
        }

        mock_claude_response = MagicMock()
        mock_claude_response.content = [
            MagicMock(text=json.dumps(briefing_response))
        ]

        with (
            patch("agents.synthesis_agent.settings") as mock_settings,
            patch("agents.synthesis_agent.anthropic") as mock_anthropic_mod,
        ):
            mock_settings.anthropic.api_key = "test-key"
            mock_settings.anthropic.synthesis_model = "claude-sonnet-4-20250514"
            mock_settings.anthropic.max_tokens_synthesis = 8192
            mock_settings.anthropic.temperature_synthesis = 0.3

            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_claude_response)
            mock_anthropic_mod.AsyncAnthropic.return_value = mock_client

            result = await synthesis_agent(sample_pipeline_state)

        assert "ML Investment" in result["briefing"]["top_insights"][0]["title"]
        assert len(result["insights"]) >= 1

    @pytest.mark.asyncio
    async def test_handles_json_parse_error(
        self, sample_pipeline_state: dict
    ) -> None:
        mock_claude_response = MagicMock()
        mock_claude_response.content = [MagicMock(text="not valid json {{{")]

        with (
            patch("agents.synthesis_agent.settings") as mock_settings,
            patch("agents.synthesis_agent.anthropic") as mock_anthropic_mod,
        ):
            mock_settings.anthropic.api_key = "test-key"
            mock_settings.anthropic.synthesis_model = "claude-sonnet-4-20250514"
            mock_settings.anthropic.max_tokens_synthesis = 8192
            mock_settings.anthropic.temperature_synthesis = 0.3

            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_claude_response)
            mock_anthropic_mod.AsyncAnthropic.return_value = mock_client

            result = await synthesis_agent(sample_pipeline_state)

        assert result["briefing"]["executive_summary"] == "Insufficient data to generate a briefing."
        assert any("JSON" in e.get("error", "") for e in result["errors"])

    @pytest.mark.asyncio
    async def test_briefing_structure_validation(self) -> None:
        """Verify the briefing structure matches the expected schema."""
        briefing = _empty_briefing()
        required_keys = {
            "executive_summary",
            "top_insights",
            "predictive_signals",
            "recommended_plays",
            "competitor_summaries",
            "generated_at",
        }
        assert set(briefing.keys()) == required_keys
