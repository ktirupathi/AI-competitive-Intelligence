"""Competitor CRUD routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status

from ..deps import CurrentUser, DbSession
from ..schemas.competitor import (
    ChangeRead,
    CompetitorCreate,
    CompetitorDetail,
    CompetitorListResponse,
    CompetitorRead,
    CompetitorUpdate,
    JobPostingRead,
    NewsItemRead,
    ReviewRead,
    SocialPostRead,
)
from ..services.competitor_service import CompetitorService

router = APIRouter()


@router.get("", response_model=CompetitorListResponse)
async def list_competitors(
    db: DbSession,
    user: CurrentUser,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> CompetitorListResponse:
    """List all competitors for the current user."""
    service = CompetitorService(db)
    items, total = await service.list_competitors(user.id, offset, limit)
    return CompetitorListResponse(
        items=[CompetitorRead.model_validate(c) for c in items],
        total=total,
    )


@router.get("/{competitor_id}", response_model=CompetitorDetail)
async def get_competitor(
    competitor_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> CompetitorDetail:
    """Get a single competitor with activity counts."""
    service = CompetitorService(db)
    competitor = await service.get_competitor(competitor_id, user.id)
    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )
    counts = await service.get_activity_counts(competitor_id)
    data = CompetitorRead.model_validate(competitor).model_dump()
    data.update(counts)
    return CompetitorDetail(**data)


@router.post("", response_model=CompetitorRead, status_code=status.HTTP_201_CREATED)
async def create_competitor(
    data: CompetitorCreate,
    db: DbSession,
    user: CurrentUser,
) -> CompetitorRead:
    """Create a new competitor to monitor."""
    service = CompetitorService(db)
    try:
        competitor = await service.create_competitor(user, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(exc),
        )
    await db.commit()
    return CompetitorRead.model_validate(competitor)


@router.patch("/{competitor_id}", response_model=CompetitorRead)
async def update_competitor(
    competitor_id: uuid.UUID,
    data: CompetitorUpdate,
    db: DbSession,
    user: CurrentUser,
) -> CompetitorRead:
    """Update a competitor's details."""
    service = CompetitorService(db)
    competitor = await service.update_competitor(competitor_id, user.id, data)
    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )
    await db.commit()
    return CompetitorRead.model_validate(competitor)


@router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_competitor(
    competitor_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> None:
    """Delete a competitor and all associated data."""
    service = CompetitorService(db)
    deleted = await service.delete_competitor(competitor_id, user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )
    await db.commit()


@router.get("/{competitor_id}/changes", response_model=dict)
async def list_competitor_changes(
    competitor_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    since: datetime | None = Query(None),
) -> dict:
    """List detected changes for a competitor."""
    service = CompetitorService(db)
    items, total = await service.get_competitor_changes(
        competitor_id, user.id, offset, limit, since
    )
    return {
        "items": [ChangeRead.model_validate(c) for c in items],
        "total": total,
    }


@router.get("/{competitor_id}/news", response_model=dict)
async def list_competitor_news(
    competitor_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> dict:
    """List news items for a competitor."""
    service = CompetitorService(db)
    items, total = await service.get_competitor_news(
        competitor_id, user.id, offset, limit
    )
    return {
        "items": [NewsItemRead.model_validate(n) for n in items],
        "total": total,
    }


@router.get("/{competitor_id}/jobs", response_model=dict)
async def list_competitor_jobs(
    competitor_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    active_only: bool = Query(True),
) -> dict:
    """List job postings for a competitor."""
    service = CompetitorService(db)
    items, total = await service.get_competitor_jobs(
        competitor_id, user.id, active_only, offset, limit
    )
    return {
        "items": [JobPostingRead.model_validate(j) for j in items],
        "total": total,
    }


@router.get("/{competitor_id}/reviews", response_model=dict)
async def list_competitor_reviews(
    competitor_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> dict:
    """List reviews for a competitor."""
    service = CompetitorService(db)
    items, total = await service.get_competitor_reviews(
        competitor_id, user.id, offset, limit
    )
    return {
        "items": [ReviewRead.model_validate(r) for r in items],
        "total": total,
    }


@router.get("/{competitor_id}/social", response_model=dict)
async def list_competitor_social(
    competitor_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> dict:
    """List social posts for a competitor."""
    service = CompetitorService(db)
    items, total = await service.get_competitor_social(
        competitor_id, user.id, offset, limit
    )
    return {
        "items": [SocialPostRead.model_validate(s) for s in items],
        "total": total,
    }
