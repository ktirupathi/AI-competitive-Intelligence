"""Pydantic schemas for admin endpoints."""

from datetime import datetime

from pydantic import BaseModel


class AgentHealthStatus(BaseModel):
    agent_name: str
    last_run: datetime | None = None
    status: str  # running | success | failed | no_runs
    error_count: int = 0
    total_runs: int = 0
    avg_duration_seconds: float | None = None
    last_error: str | None = None


class AgentHealthResponse(BaseModel):
    agents: list[AgentHealthStatus]
    total_agents: int
