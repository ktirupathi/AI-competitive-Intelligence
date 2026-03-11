"""Tests for the agents.logging module (timing tracker & agent logger)."""

from __future__ import annotations

import logging
import time

import pytest

from agents.logging import TimingTracker, get_agent_logger


class TestGetAgentLogger:
    """Tests for the get_agent_logger helper."""

    def test_returns_logger_with_correct_name(self) -> None:
        lg = get_agent_logger("web_monitor")
        assert lg.name == "scoutai.agents.web_monitor"
        assert isinstance(lg, logging.Logger)

    def test_different_agents_get_different_loggers(self) -> None:
        a = get_agent_logger("news")
        b = get_agent_logger("review")
        assert a is not b
        assert a.name != b.name


class TestTimingTracker:
    """Tests for the TimingTracker class."""

    def test_track_records_duration(self) -> None:
        tracker = TimingTracker()
        with tracker.track("test_agent"):
            time.sleep(0.01)
        snap = tracker.snapshot()
        assert "test_agent" in snap
        assert snap["test_agent"]["call_count"] == 1
        assert snap["test_agent"]["total_seconds"] > 0
        assert snap["test_agent"]["errors"] == 0

    def test_track_accumulates_calls(self) -> None:
        tracker = TimingTracker()
        for _ in range(3):
            with tracker.track("counter"):
                pass
        snap = tracker.snapshot()
        assert snap["counter"]["call_count"] == 3

    def test_track_records_errors(self) -> None:
        tracker = TimingTracker()
        with pytest.raises(ValueError):
            with tracker.track("failing"):
                raise ValueError("boom")
        snap = tracker.snapshot()
        assert snap["failing"]["errors"] == 1
        assert snap["failing"]["call_count"] == 1

    def test_snapshot_is_json_serialisable(self) -> None:
        import json

        tracker = TimingTracker()
        with tracker.track("json_test"):
            pass
        serialised = json.dumps(tracker.snapshot())
        assert "json_test" in serialised

    def test_reset_clears_all_data(self) -> None:
        tracker = TimingTracker()
        with tracker.track("ephemeral"):
            pass
        tracker.reset()
        assert tracker.snapshot() == {}

    def test_avg_duration_calculated(self) -> None:
        tracker = TimingTracker()
        with tracker.track("avg"):
            time.sleep(0.01)
        with tracker.track("avg"):
            time.sleep(0.01)
        snap = tracker.snapshot()
        assert snap["avg"]["avg_duration_seconds"] > 0
        assert snap["avg"]["avg_duration_seconds"] <= snap["avg"]["total_seconds"]

    def test_multiple_agents_independent(self) -> None:
        tracker = TimingTracker()
        with tracker.track("alpha"):
            pass
        with tracker.track("beta"):
            pass
        snap = tracker.snapshot()
        assert "alpha" in snap
        assert "beta" in snap
        assert snap["alpha"]["call_count"] == 1
        assert snap["beta"]["call_count"] == 1
