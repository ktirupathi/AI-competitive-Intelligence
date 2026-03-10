"""Admin routes: agent health monitoring and operational tools."""

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import case, distinct, func, select

from ..deps import CurrentUser, DbSession
from ..models.alert import AgentRun
from ..schemas.admin import AgentHealthResponse, AgentHealthStatus

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/agents", response_model=AgentHealthResponse)
async def get_agent_health(
    db: DbSession,
    user: CurrentUser,
) -> AgentHealthResponse:
    """Get health status for all monitored agents.

    Returns last run time, status, error counts, and average duration.
    """
    # Get distinct agent names
    agent_names_q = select(distinct(AgentRun.agent_name))
    result = await db.execute(agent_names_q)
    agent_names = [row[0] for row in result.all()]

    agents = []
    for name in agent_names:
        # Get latest run
        latest_q = (
            select(AgentRun)
            .where(AgentRun.agent_name == name)
            .order_by(AgentRun.started_at.desc())
            .limit(1)
        )
        latest_result = await db.execute(latest_q)
        latest_run = latest_result.scalar_one_or_none()

        # Get aggregate stats
        stats_q = select(
            func.count().label("total_runs"),
            func.count()
            .filter(AgentRun.status == "failed")
            .label("error_count"),
            func.avg(AgentRun.duration_seconds).label("avg_duration"),
        ).where(AgentRun.agent_name == name)
        stats_result = await db.execute(stats_q)
        stats = stats_result.one()

        # Get last error message
        last_error_q = (
            select(AgentRun.error_message)
            .where(
                AgentRun.agent_name == name,
                AgentRun.status == "failed",
            )
            .order_by(AgentRun.started_at.desc())
            .limit(1)
        )
        last_error_result = await db.execute(last_error_q)
        last_error_row = last_error_result.scalar_one_or_none()

        agents.append(
            AgentHealthStatus(
                agent_name=name,
                last_run=latest_run.started_at if latest_run else None,
                status=latest_run.status if latest_run else "no_runs",
                error_count=stats.error_count or 0,
                total_runs=stats.total_runs or 0,
                avg_duration_seconds=(
                    float(stats.avg_duration) if stats.avg_duration else None
                ),
                last_error=last_error_row,
            )
        )

    return AgentHealthResponse(agents=agents, total_agents=len(agents))


@router.get("/audit-logs")
async def list_audit_logs(
    db: DbSession,
    user: CurrentUser,
    workspace_id: str | None = None,
    action: str | None = None,
    resource: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> dict:
    """List audit logs (admin only)."""
    import uuid

    from ..schemas.audit_log import AuditLogListResponse, AuditLogRead
    from ..services.audit_log_service import AuditLogService

    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace_id is required",
        )

    service = AuditLogService(db)
    items, total = await service.list_logs(
        workspace_id=uuid.UUID(workspace_id),
        action=action,
        resource=resource,
        offset=offset,
        limit=limit,
    )
    return AuditLogListResponse(
        items=[AuditLogRead.model_validate(i) for i in items],
        total=total,
    ).model_dump()
