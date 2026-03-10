"""Observability metrics endpoint.

Returns per-agent timing stats collected by the pipeline's
``TimingTracker`` singleton.  Useful for dashboards and alerting
without a full Prometheus/Grafana stack.
"""

from fastapi import APIRouter

from agents.logging import timing_tracker

router = APIRouter()


@router.get("")
async def get_metrics() -> dict:
    """Return per-agent timing statistics from the current process."""
    return {
        "agents": timing_tracker.snapshot(),
    }
