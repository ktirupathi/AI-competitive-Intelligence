"""Tests for the job posting agent."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.job_agent import _extract_job_blocks, job_agent


class TestExtractJobBlocks:
    """Tests for heuristic job extraction from careers pages."""

    def test_extracts_markdown_headings(self) -> None:
        content = """
## Senior Software Engineer
Department: Engineering
Location: San Francisco

Build scalable systems for our platform.

## Product Manager
Department: Product
Location: New York

Lead product strategy for our enterprise suite.
"""
        jobs = _extract_job_blocks(content)
        assert len(jobs) >= 2
        assert jobs[0]["title"] == "Senior Software Engineer"

    def test_extracts_line_based_jobs(self) -> None:
        content = """
Open Positions

Senior Data Scientist
Data team, Remote

Machine Learning Engineer
AI team, San Francisco

Frontend Developer
Product team, NYC
"""
        jobs = _extract_job_blocks(content)
        assert len(jobs) >= 2

    def test_filters_out_non_job_headings(self) -> None:
        content = """
## Careers at Acme
We're hiring great people.

## Our Culture
We believe in collaboration.

## Senior Engineer
Department: Engineering
Location: Remote

Join our team.

## Perks and Benefits
Free lunch and gym membership.
"""
        jobs = _extract_job_blocks(content)
        titles = [j["title"].lower() for j in jobs]
        assert not any("career" in t for t in titles)
        assert not any("culture" in t for t in titles)
        assert not any("perk" in t for t in titles)

    def test_caps_at_50_jobs(self) -> None:
        lines = []
        for i in range(60):
            lines.append(f"## Software Engineer {i}\nDepartment: Engineering\nLocation: Remote\n")
        content = "\n".join(lines)
        jobs = _extract_job_blocks(content)
        assert len(jobs) <= 50

    def test_empty_content(self) -> None:
        assert _extract_job_blocks("") == []

    def test_no_matching_content(self) -> None:
        content = "This is a company homepage with no job listings."
        assert _extract_job_blocks(content) == []


class TestJobAgent:
    """Tests for the main job_agent function."""

    @pytest.mark.asyncio
    async def test_processes_competitor_careers(
        self, sample_competitor: dict
    ) -> None:
        state: dict[str, Any] = {
            "competitors": [sample_competitor],
            "errors": [],
        }

        careers_content = """
## Senior ML Engineer
Department: AI
Location: Remote

Build cutting-edge ML models.
"""
        analysis_response = {
            "seniority": "senior",
            "department": "engineering",
            "strategic_signal": "Investing in ML capabilities",
            "technologies_mentioned": ["Python", "TensorFlow"],
            "urgency_indicators": "high",
        }

        mock_claude_response = MagicMock()
        mock_claude_response.content = [
            MagicMock(text=json.dumps(analysis_response))
        ]

        with (
            patch("agents.job_agent._scrape_careers_page", new_callable=AsyncMock) as mock_scrape,
            patch("agents.job_agent.httpx.AsyncClient") as mock_http_cls,
            patch("agents.job_agent.settings") as mock_settings,
            patch("agents.job_agent.anthropic") as mock_anthropic_mod,
        ):
            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_scrape.return_value = careers_content
            mock_settings.pipeline.max_concurrent_competitors = 5
            mock_settings.anthropic.api_key = "test-key"
            mock_settings.anthropic.classification_model = "claude-haiku-4-5-20251001"
            mock_settings.anthropic.max_tokens_classification = 2048
            mock_settings.anthropic.temperature_classification = 0.1

            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_claude_response)
            mock_anthropic_mod.AsyncAnthropic.return_value = mock_client

            result = await job_agent(state)

        postings = result.get("job_postings", [])
        assert len(postings) >= 1
        assert postings[0]["department"] == "engineering"

    @pytest.mark.asyncio
    async def test_handles_no_careers_page(self, sample_competitor: dict) -> None:
        state: dict[str, Any] = {
            "competitors": [sample_competitor],
            "errors": [],
        }

        with (
            patch("agents.job_agent._scrape_careers_page", new_callable=AsyncMock) as mock_scrape,
            patch("agents.job_agent.httpx.AsyncClient") as mock_http_cls,
            patch("agents.job_agent.settings") as mock_settings,
        ):
            mock_http = AsyncMock()
            mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_scrape.return_value = ""
            mock_settings.pipeline.max_concurrent_competitors = 5

            result = await job_agent(state)

        assert result.get("job_postings", []) == []

    @pytest.mark.asyncio
    async def test_pattern_extraction_integration(self) -> None:
        """Test that job patterns are correctly extracted and structured."""
        content = """
## Head of Engineering
Department: Engineering
Location: San Francisco

Lead a team of 50+ engineers building our platform.

## VP of Sales
Department: Sales
Location: New York

Drive revenue growth for our enterprise segment.
"""
        jobs = _extract_job_blocks(content)
        # Should extract leadership/exec roles
        titles = [j["title"] for j in jobs]
        assert any("Head of Engineering" in t for t in titles)
