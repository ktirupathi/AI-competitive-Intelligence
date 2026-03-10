"""Structured logging and per-agent timing for the Scout AI pipeline.

Provides a ``get_agent_logger`` helper that returns a stdlib logger
enriched with a consistent agent-name prefix, plus a ``TimingTracker``
singleton that records per-agent durations for observability.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Generator


# ---------------------------------------------------------------------------
# Per-agent timing
# ---------------------------------------------------------------------------
@dataclass
class _TimingEntry:
    """Accumulated timing stats for one agent."""

    total_seconds: float = 0.0
    call_count: int = 0
    last_duration: float = 0.0
    errors: int = 0


class TimingTracker:
    """Thread-safe singleton that records per-agent execution durations.

    Usage::

        with timing_tracker.track("web_monitor"):
            await web_monitor_agent(state)
    """

    def __init__(self) -> None:
        self._entries: dict[str, _TimingEntry] = {}
        self._lock = Lock()

    @contextmanager
    def track(self, agent_name: str) -> Generator[None, None, None]:
        """Context manager that measures wall-clock duration for *agent_name*."""
        start = time.monotonic()
        error = False
        try:
            yield
        except Exception:
            error = True
            raise
        finally:
            elapsed = time.monotonic() - start
            with self._lock:
                entry = self._entries.setdefault(agent_name, _TimingEntry())
                entry.total_seconds += elapsed
                entry.call_count += 1
                entry.last_duration = elapsed
                if error:
                    entry.errors += 1

    def snapshot(self) -> dict[str, dict[str, Any]]:
        """Return a JSON-serialisable copy of all timing data."""
        with self._lock:
            return {
                name: {
                    "total_seconds": round(e.total_seconds, 3),
                    "call_count": e.call_count,
                    "last_duration_seconds": round(e.last_duration, 3),
                    "avg_duration_seconds": round(
                        e.total_seconds / e.call_count, 3
                    )
                    if e.call_count
                    else 0.0,
                    "errors": e.errors,
                }
                for name, e in self._entries.items()
            }

    def reset(self) -> None:
        """Clear all recorded timings (useful for testing)."""
        with self._lock:
            self._entries.clear()


# Module-level singleton
timing_tracker = TimingTracker()


# ---------------------------------------------------------------------------
# Agent logger helper
# ---------------------------------------------------------------------------
def get_agent_logger(agent_name: str) -> logging.Logger:
    """Return a logger namespaced under ``scoutai.agents.<agent_name>``."""
    return logging.getLogger(f"scoutai.agents.{agent_name}")
