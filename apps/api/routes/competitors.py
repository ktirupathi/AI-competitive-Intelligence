"""Competitor CRUD routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import CurrentUser, DbSession
from ..models.change import Change
from ..models.job_posting import JobPosting
from ..models.news import NewsItem
from ..models.review import Review
from ..models.social_post import SocialPost
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
from ..services.audit_log_service import log_action
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
    await log_action(
        db,
        action="create",
        resource="competitor",
        user_id=user.id,
        resource_id=str(competitor.id),
        metadata={"name": competitor.name, "domain": competitor.domain},
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
    await log_action(
        db,
        action="delete",
        resource="competitor",
        user_id=user.id,
        resource_id=str(competitor_id),
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


@router.get("/{competitor_id}/timeline")
async def get_competitor_timeline(
    competitor_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    since: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Get a unified chronological timeline of all signals for a competitor.

    Combines website changes, job postings, news, reviews, and social posts
    into a single sorted timeline.
    """
    service = CompetitorService(db)
    competitor = await service.get_competitor(competitor_id, user.id)
    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )

    from sqlalchemy import literal_column

    timeline = []

    # Website changes
    changes_q = select(Change).where(Change.competitor_id == competitor_id)
    if since:
        changes_q = changes_q.where(Change.detected_at >= since)
    changes_q = changes_q.order_by(Change.detected_at.desc()).limit(limit)
    changes_result = await db.execute(changes_q)
    for ch in changes_result.scalars().all():
        timeline.append({
            "type": "change",
            "id": str(ch.id),
            "title": ch.title,
            "summary": ch.summary,
            "severity": ch.severity,
            "timestamp": ch.detected_at.isoformat() if ch.detected_at else None,
            "metadata": {"change_type": ch.change_type, "page_url": ch.page_url},
        })

    # News items
    news_q = select(NewsItem).where(NewsItem.competitor_id == competitor_id)
    if since:
        news_q = news_q.where(NewsItem.discovered_at >= since)
    news_q = news_q.order_by(NewsItem.discovered_at.desc()).limit(limit)
    news_result = await db.execute(news_q)
    for n in news_result.scalars().all():
        timeline.append({
            "type": "news",
            "id": str(n.id),
            "title": n.title,
            "summary": n.summary,
            "severity": None,
            "timestamp": (n.published_at or n.discovered_at).isoformat(),
            "metadata": {"source": n.source, "url": n.url, "sentiment": n.sentiment},
        })

    # Job postings
    jobs_q = select(JobPosting).where(JobPosting.competitor_id == competitor_id)
    if since:
        jobs_q = jobs_q.where(JobPosting.discovered_at >= since)
    jobs_q = jobs_q.order_by(JobPosting.discovered_at.desc()).limit(limit)
    jobs_result = await db.execute(jobs_q)
    for j in jobs_result.scalars().all():
        timeline.append({
            "type": "job",
            "id": str(j.id),
            "title": j.title,
            "summary": f"{j.department or 'Unknown dept'} - {j.location or 'Unknown location'}",
            "severity": None,
            "timestamp": (j.posted_at or j.discovered_at).isoformat(),
            "metadata": {"department": j.department, "url": j.url, "is_active": j.is_active},
        })

    # Reviews
    reviews_q = select(Review).where(Review.competitor_id == competitor_id)
    if since:
        reviews_q = reviews_q.where(Review.discovered_at >= since)
    reviews_q = reviews_q.order_by(Review.discovered_at.desc()).limit(limit)
    reviews_result = await db.execute(reviews_q)
    for r in reviews_result.scalars().all():
        timeline.append({
            "type": "review",
            "id": str(r.id),
            "title": r.title or f"Review on {r.platform}",
            "summary": (r.body or "")[:200],
            "severity": None,
            "timestamp": (r.reviewed_at or r.discovered_at).isoformat() if (r.reviewed_at or r.discovered_at) else None,
            "metadata": {"platform": r.platform, "rating": r.rating, "sentiment": r.sentiment},
        })

    # Social posts
    social_q = select(SocialPost).where(SocialPost.competitor_id == competitor_id)
    if since:
        social_q = social_q.where(SocialPost.discovered_at >= since)
    social_q = social_q.order_by(SocialPost.discovered_at.desc()).limit(limit)
    social_result = await db.execute(social_q)
    for s in social_result.scalars().all():
        timeline.append({
            "type": "social",
            "id": str(s.id),
            "title": f"{s.platform} post",
            "summary": (s.content or "")[:200],
            "severity": None,
            "timestamp": (s.posted_at or s.discovered_at).isoformat() if (s.posted_at or s.discovered_at) else None,
            "metadata": {"platform": s.platform, "url": s.url, "engagement_rate": s.engagement_rate},
        })

    # Sort all events by timestamp descending
    timeline.sort(
        key=lambda x: x.get("timestamp") or "1970-01-01T00:00:00",
        reverse=True,
    )

    return {
        "competitor_id": str(competitor_id),
        "competitor_name": competitor.name,
        "events": timeline[:limit],
        "total": len(timeline),
    }
