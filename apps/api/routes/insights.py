"""Insight routes: list, filter, mark as read, dismiss."""

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select, update

from ..deps import CurrentUser, DbSession
from ..models.competitor import Competitor
from ..models.insight import Insight
from ..schemas.insight import (
    InsightDismiss,
    InsightListResponse,
    InsightMarkRead,
    InsightRead,
)

router = APIRouter()


@router.get("", response_model=InsightListResponse)
async def list_insights(
    db: DbSession,
    user: CurrentUser,
    competitor_id: uuid.UUID | None = Query(None),
    category: str | None = Query(None),
    severity: str | None = Query(None),
    is_read: bool | None = Query(None),
    is_dismissed: bool | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> InsightListResponse:
    """List insights across all of the user's competitors, with filters."""
    # Get the user's competitor IDs
    comp_ids_q = select(Competitor.id).where(Competitor.user_id == user.id)
    comp_result = await db.execute(comp_ids_q)
    comp_ids = [row[0] for row in comp_result.all()]

    if not comp_ids:
        return InsightListResponse(items=[], total=0)

    base = select(Insight).where(Insight.competitor_id.in_(comp_ids))

    if competitor_id is not None:
        if competitor_id not in comp_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competitor not found",
            )
        base = base.where(Insight.competitor_id == competitor_id)

    if category is not None:
        base = base.where(Insight.category == category)
    if severity is not None:
        base = base.where(Insight.severity == severity)
    if is_read is not None:
        base = base.where(Insight.is_read == is_read)
    if is_dismissed is not None:
        base = base.where(Insight.is_dismissed == is_dismissed)

    # Count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Fetch
    query = base.order_by(Insight.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return InsightListResponse(
        items=[InsightRead.model_validate(i) for i in items],
        total=total,
    )


@router.get("/{insight_id}", response_model=InsightRead)
async def get_insight(
    insight_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> InsightRead:
    """Get a single insight by ID."""
    # Verify the insight belongs to one of the user's competitors
    comp_ids_q = select(Competitor.id).where(Competitor.user_id == user.id)
    comp_result = await db.execute(comp_ids_q)
    comp_ids = [row[0] for row in comp_result.all()]

    result = await db.execute(
        select(Insight).where(
            Insight.id == insight_id,
            Insight.competitor_id.in_(comp_ids),
        )
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        )
    return InsightRead.model_validate(insight)


@router.post("/mark-read", status_code=status.HTTP_200_OK)
async def mark_insights_read(
    data: InsightMarkRead,
    db: DbSession,
    user: CurrentUser,
) -> dict[str, int]:
    """Mark one or more insights as read."""
    comp_ids_q = select(Competitor.id).where(Competitor.user_id == user.id)
    comp_result = await db.execute(comp_ids_q)
    comp_ids = [row[0] for row in comp_result.all()]

    stmt = (
        update(Insight)
        .where(
            Insight.id.in_(data.insight_ids),
            Insight.competitor_id.in_(comp_ids),
        )
        .values(is_read=True)
    )
    result = await db.execute(stmt)
    await db.commit()
    return {"updated": result.rowcount}


@router.post("/dismiss", status_code=status.HTTP_200_OK)
async def dismiss_insights(
    data: InsightDismiss,
    db: DbSession,
    user: CurrentUser,
) -> dict[str, int]:
    """Dismiss one or more insights."""
    comp_ids_q = select(Competitor.id).where(Competitor.user_id == user.id)
    comp_result = await db.execute(comp_ids_q)
    comp_ids = [row[0] for row in comp_result.all()]

    stmt = (
        update(Insight)
        .where(
            Insight.id.in_(data.insight_ids),
            Insight.competitor_id.in_(comp_ids),
        )
        .values(is_dismissed=True)
    )
    result = await db.execute(stmt)
    await db.commit()
    return {"updated": result.rowcount}
