"""Service layer for competitor operations."""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.change import Change
from ..models.competitor import Competitor
from ..models.insight import Insight
from ..models.job_posting import JobPosting
from ..models.news import NewsItem
from ..models.review import Review
from ..models.social_post import SocialPost
from ..models.user import User
from ..schemas.competitor import CompetitorCreate, CompetitorUpdate

logger = logging.getLogger(__name__)


class CompetitorService:
    """Handles competitor CRUD and related data retrieval."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_competitors(
        self,
        user_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Competitor], int]:
        """List all competitors for a user with pagination."""
        count_query = select(func.count()).where(Competitor.user_id == user_id)
        total = (await self.db.execute(count_query)).scalar() or 0

        query = (
            select(Competitor)
            .where(Competitor.user_id == user_id)
            .order_by(Competitor.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_competitor(
        self, competitor_id: uuid.UUID, user_id: uuid.UUID
    ) -> Competitor | None:
        """Get a single competitor by ID, scoped to user."""
        query = select(Competitor).where(
            Competitor.id == competitor_id,
            Competitor.user_id == user_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_competitor(
        self, user: User, data: CompetitorCreate
    ) -> Competitor:
        """Create a new competitor for a user, enforcing plan limits."""
        count_query = select(func.count()).where(Competitor.user_id == user.id)
        current_count = (await self.db.execute(count_query)).scalar() or 0

        if current_count >= user.plan_competitor_limit:
            raise ValueError(
                f"Competitor limit reached ({user.plan_competitor_limit}). "
                "Upgrade your plan to add more."
            )

        competitor = Competitor(
            user_id=user.id,
            **data.model_dump(),
        )
        self.db.add(competitor)
        await self.db.flush()
        await self.db.refresh(competitor)
        logger.info("Created competitor %s for user %s", competitor.id, user.id)
        return competitor

    async def update_competitor(
        self,
        competitor_id: uuid.UUID,
        user_id: uuid.UUID,
        data: CompetitorUpdate,
    ) -> Competitor | None:
        """Update a competitor's details."""
        competitor = await self.get_competitor(competitor_id, user_id)
        if competitor is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(competitor, field, value)

        await self.db.flush()
        await self.db.refresh(competitor)
        return competitor

    async def delete_competitor(
        self, competitor_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Delete a competitor and all related data (cascades)."""
        competitor = await self.get_competitor(competitor_id, user_id)
        if competitor is None:
            return False
        await self.db.delete(competitor)
        await self.db.flush()
        logger.info("Deleted competitor %s", competitor_id)
        return True

    async def get_competitor_changes(
        self,
        competitor_id: uuid.UUID,
        user_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
        since: datetime | None = None,
    ) -> tuple[list[Change], int]:
        """Get changes detected for a competitor."""
        # Verify ownership
        competitor = await self.get_competitor(competitor_id, user_id)
        if competitor is None:
            return [], 0

        base = select(Change).where(Change.competitor_id == competitor_id)
        if since:
            base = base.where(Change.detected_at >= since)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        query = base.order_by(Change.detected_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_competitor_news(
        self,
        competitor_id: uuid.UUID,
        user_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[NewsItem], int]:
        """Get news items for a competitor."""
        competitor = await self.get_competitor(competitor_id, user_id)
        if competitor is None:
            return [], 0

        count_q = select(func.count()).where(NewsItem.competitor_id == competitor_id)
        total = (await self.db.execute(count_q)).scalar() or 0

        query = (
            select(NewsItem)
            .where(NewsItem.competitor_id == competitor_id)
            .order_by(NewsItem.discovered_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_competitor_jobs(
        self,
        competitor_id: uuid.UUID,
        user_id: uuid.UUID,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[JobPosting], int]:
        """Get job postings for a competitor."""
        competitor = await self.get_competitor(competitor_id, user_id)
        if competitor is None:
            return [], 0

        base = select(JobPosting).where(JobPosting.competitor_id == competitor_id)
        if active_only:
            base = base.where(JobPosting.is_active.is_(True))

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        query = base.order_by(JobPosting.discovered_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_competitor_reviews(
        self,
        competitor_id: uuid.UUID,
        user_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Review], int]:
        """Get reviews for a competitor."""
        competitor = await self.get_competitor(competitor_id, user_id)
        if competitor is None:
            return [], 0

        count_q = select(func.count()).where(Review.competitor_id == competitor_id)
        total = (await self.db.execute(count_q)).scalar() or 0

        query = (
            select(Review)
            .where(Review.competitor_id == competitor_id)
            .order_by(Review.discovered_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_competitor_social(
        self,
        competitor_id: uuid.UUID,
        user_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[SocialPost], int]:
        """Get social posts for a competitor."""
        competitor = await self.get_competitor(competitor_id, user_id)
        if competitor is None:
            return [], 0

        count_q = select(func.count()).where(SocialPost.competitor_id == competitor_id)
        total = (await self.db.execute(count_q)).scalar() or 0

        query = (
            select(SocialPost)
            .where(SocialPost.competitor_id == competitor_id)
            .order_by(SocialPost.discovered_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_activity_counts(
        self, competitor_id: uuid.UUID, days: int = 30
    ) -> dict[str, int]:
        """Get recent activity counts for a competitor."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        changes = (
            await self.db.execute(
                select(func.count()).where(
                    Change.competitor_id == competitor_id,
                    Change.detected_at >= since,
                )
            )
        ).scalar() or 0

        news = (
            await self.db.execute(
                select(func.count()).where(
                    NewsItem.competitor_id == competitor_id,
                    NewsItem.discovered_at >= since,
                )
            )
        ).scalar() or 0

        jobs = (
            await self.db.execute(
                select(func.count()).where(
                    JobPosting.competitor_id == competitor_id,
                    JobPosting.is_active.is_(True),
                )
            )
        ).scalar() or 0

        insights = (
            await self.db.execute(
                select(func.count()).where(
                    Insight.competitor_id == competitor_id,
                    Insight.created_at >= since,
                )
            )
        ).scalar() or 0

        return {
            "recent_changes_count": changes,
            "recent_news_count": news,
            "active_job_count": jobs,
            "recent_insights_count": insights,
        }
