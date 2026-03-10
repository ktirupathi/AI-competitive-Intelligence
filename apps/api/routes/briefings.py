"""Briefing routes: list, get, generate, and history."""

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import select

from ..deps import CurrentUser, DbSession
from ..models.briefing import Briefing
from ..models.competitor import Competitor
from ..schemas.briefing import (
    BriefingGenerateRequest,
    BriefingListResponse,
    BriefingRead,
    BriefingSummary,
)
from ..services.audit_log_service import log_action
from ..services.briefing_service import BriefingService

router = APIRouter()


@router.get("", response_model=BriefingListResponse)
async def list_briefings(
    db: DbSession,
    user: CurrentUser,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
) -> BriefingListResponse:
    """List all briefings for the current user."""
    service = BriefingService(db)
    items, total = await service.list_briefings(user.id, offset, limit)
    return BriefingListResponse(
        items=[BriefingRead.model_validate(b) for b in items],
        total=total,
    )


@router.get("/latest", response_model=BriefingRead | None)
async def get_latest_briefing(
    db: DbSession,
    user: CurrentUser,
) -> BriefingRead | None:
    """Get the most recent briefing."""
    service = BriefingService(db)
    items, _ = await service.list_briefings(user.id, offset=0, limit=1)
    if not items:
        return None
    return BriefingRead.model_validate(items[0])


@router.get("/{briefing_id}", response_model=BriefingRead)
async def get_briefing(
    briefing_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> BriefingRead:
    """Get a single briefing by ID."""
    service = BriefingService(db)
    briefing = await service.get_briefing(briefing_id, user.id)
    if not briefing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Briefing not found",
        )
    return BriefingRead.model_validate(briefing)


@router.post("/generate", response_model=BriefingRead, status_code=status.HTTP_201_CREATED)
async def generate_briefing(
    data: BriefingGenerateRequest,
    db: DbSession,
    user: CurrentUser,
) -> BriefingRead:
    """Manually trigger briefing generation.

    This calls Claude to analyze recent competitor activity and produce
    a structured intelligence briefing.
    """
    service = BriefingService(db)
    try:
        briefing = await service.generate_briefing(
            user=user,
            competitor_ids=data.competitor_ids,
            frequency=data.frequency,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    await log_action(
        db,
        action="generate",
        resource="briefing",
        user_id=user.id,
        resource_id=str(briefing.id),
    )
    await db.commit()
    return BriefingRead.model_validate(briefing)


@router.get("/history", response_model=BriefingListResponse)
async def briefing_history(
    db: DbSession,
    user: CurrentUser,
    competitor_id: uuid.UUID | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    frequency: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> BriefingListResponse:
    """Get briefing history with filtering by competitor, date range, and frequency."""
    from sqlalchemy import func

    base = select(Briefing).where(Briefing.user_id == user.id)

    if date_from:
        base = base.where(Briefing.period_start >= date_from)
    if date_to:
        base = base.where(Briefing.period_end <= date_to)
    if frequency:
        base = base.where(Briefing.frequency == frequency)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = base.order_by(Briefing.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return BriefingListResponse(
        items=[BriefingRead.model_validate(b) for b in items],
        total=total,
    )
