"""Tests for the pipeline orchestration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.pipeline import (
    _with_retries,
    build_pipeline,
    build_pipeline_sequential,
    node_collect,
    run_pipeline,
)


class TestWithRetries:
    """Tests for the retry logic wrapper."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(self) -> None:
        async def success_fn(state: dict) -> dict:
            return {"result": "ok"}

        with patch("agents.pipeline.settings") as mock_settings:
            mock_settings.pipeline.agent_max_retries = 3
            mock_settings.pipeline.agent_retry_delay_seconds = 0.01

            result = await _with_retries(success_fn, {"errors": []}, "test_agent")

        assert result == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_retries_on_failure(self) -> None:
        call_count = 0

        async def flaky_fn(state: dict) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Transient error")
            return {"result": "ok"}

        with patch("agents.pipeline.settings") as mock_settings:
            mock_settings.pipeline.agent_max_retries = 3
            mock_settings.pipeline.agent_retry_delay_seconds = 0.01

            result = await _with_retries(flaky_fn, {"errors": []}, "test_agent")

        assert result == {"result": "ok"}
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_returns_error_after_max_retries(self) -> None:
        async def fail_fn(state: dict) -> dict:
            raise RuntimeError("Permanent failure")

        with patch("agents.pipeline.settings") as mock_settings:
            mock_settings.pipeline.agent_max_retries = 2
            mock_settings.pipeline.agent_retry_delay_seconds = 0.01

            result = await _with_retries(fail_fn, {"errors": []}, "fail_agent")

        assert "errors" in result
        assert len(result["errors"]) == 1
        assert result["errors"][0]["agent"] == "fail_agent"
        assert "Permanent failure" in result["errors"][0]["error"]


class TestNodeCollect:
    """Tests for the parallel collection fan-out node."""

    @pytest.mark.asyncio
    async def test_merges_parallel_results(
        self, sample_pipeline_state: dict
    ) -> None:
        async def mock_web_monitor(state: dict) -> dict:
            return {"snapshots": [{"url": "https://acme.com"}], "changes": []}

        async def mock_news(state: dict) -> dict:
            return {"news_items": [{"title": "News 1"}]}

        async def mock_jobs(state: dict) -> dict:
            return {"job_postings": []}

        async def mock_reviews(state: dict) -> dict:
            return {"reviews": []}

        async def mock_social(state: dict) -> dict:
            return {"social_posts": []}

        with (
            patch("agents.pipeline.web_monitor_agent", mock_web_monitor),
            patch("agents.pipeline.news_agent", mock_news),
            patch("agents.pipeline.job_agent", mock_jobs),
            patch("agents.pipeline.review_agent", mock_reviews),
            patch("agents.pipeline.social_agent", mock_social),
            patch("agents.pipeline.settings") as mock_settings,
        ):
            mock_settings.pipeline.agent_max_retries = 1
            mock_settings.pipeline.agent_retry_delay_seconds = 0.01

            result = await node_collect(sample_pipeline_state)

        assert "snapshots" in result
        assert "news_items" in result

    @pytest.mark.asyncio
    async def test_handles_partial_failures(
        self, sample_pipeline_state: dict
    ) -> None:
        async def mock_web_monitor(state: dict) -> dict:
            return {"snapshots": [{"url": "https://acme.com"}], "changes": []}

        async def mock_news_fail(state: dict) -> dict:
            raise RuntimeError("News API down")

        async def mock_jobs(state: dict) -> dict:
            return {"job_postings": [{"title": "Engineer"}]}

        async def mock_reviews(state: dict) -> dict:
            raise RuntimeError("G2 blocked")

        async def mock_social(state: dict) -> dict:
            return {"social_posts": []}

        with (
            patch("agents.pipeline.web_monitor_agent", mock_web_monitor),
            patch("agents.pipeline.news_agent", mock_news_fail),
            patch("agents.pipeline.job_agent", mock_jobs),
            patch("agents.pipeline.review_agent", mock_reviews),
            patch("agents.pipeline.social_agent", mock_social),
            patch("agents.pipeline.settings") as mock_settings,
        ):
            mock_settings.pipeline.agent_max_retries = 1
            mock_settings.pipeline.agent_retry_delay_seconds = 0.01

            result = await node_collect(sample_pipeline_state)

        # Should still have results from successful agents
        assert "snapshots" in result or "job_postings" in result
        # Should have errors from failed agents
        assert len(result.get("errors", [])) >= 1


class TestBuildPipeline:
    """Tests for pipeline graph construction."""

    def test_build_pipeline_compiles(self) -> None:
        pipeline = build_pipeline()
        assert pipeline is not None

    def test_build_pipeline_sequential_compiles(self) -> None:
        pipeline = build_pipeline_sequential()
        assert pipeline is not None


class TestRunPipeline:
    """Tests for the full pipeline runner."""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_mocks(
        self, sample_competitors: list[dict]
    ) -> None:
        async def mock_collect(state: dict) -> dict:
            return {
                "snapshots": [],
                "changes": [],
                "news_items": [],
                "job_postings": [],
                "reviews": [],
                "social_posts": [],
                "errors": list(state.get("errors", [])),
            }

        async def mock_cluster(state: dict) -> dict:
            return {
                "signal_clusters": [],
                "errors": list(state.get("errors", [])),
            }

        async def mock_predict(state: dict) -> dict:
            return {
                "predictions": [],
                "errors": list(state.get("errors", [])),
            }

        async def mock_synthesis(state: dict) -> dict:
            return {
                "insights": [],
                "briefing": {
                    "executive_summary": "Test briefing",
                    "top_insights": [],
                    "predictive_signals": [],
                    "recommended_plays": [],
                    "competitor_summaries": [],
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
                "errors": list(state.get("errors", [])),
            }

        async def mock_delivery(state: dict) -> dict:
            return {
                "delivery_results": [],
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "errors": list(state.get("errors", [])),
            }

        with (
            patch("agents.pipeline.node_collect", mock_collect),
            patch("agents.pipeline.node_cluster_signals", mock_cluster),
            patch("agents.pipeline.node_predict", mock_predict),
            patch("agents.pipeline.node_synthesis", mock_synthesis),
            patch("agents.pipeline.node_delivery", mock_delivery),
            patch("agents.pipeline.build_pipeline") as mock_build,
        ):
            mock_graph = AsyncMock()
            mock_graph.ainvoke = AsyncMock(return_value={
                "run_id": "test-run",
                "changes": [],
                "news_items": [],
                "job_postings": [],
                "reviews": [],
                "social_posts": [],
                "insights": [],
                "briefing": {"executive_summary": "Test"},
                "delivery_results": [],
                "errors": [],
            })
            mock_build.return_value = mock_graph

            result = await run_pipeline(
                competitors=sample_competitors,
                user_email="test@example.com",
            )

        assert "run_id" in result
        assert isinstance(result.get("errors", []), list)

    @pytest.mark.asyncio
    async def test_sequential_mode(self, sample_competitors: list[dict]) -> None:
        with patch("agents.pipeline.build_pipeline_sequential") as mock_build:
            mock_graph = AsyncMock()
            mock_graph.ainvoke = AsyncMock(return_value={
                "run_id": "test-seq",
                "changes": [],
                "news_items": [],
                "job_postings": [],
                "reviews": [],
                "social_posts": [],
                "insights": [],
                "delivery_results": [],
                "errors": [],
            })
            mock_build.return_value = mock_graph

            result = await run_pipeline(
                competitors=sample_competitors,
                sequential=True,
            )

        mock_build.assert_called_once()
        assert result["run_id"] == "test-seq"
