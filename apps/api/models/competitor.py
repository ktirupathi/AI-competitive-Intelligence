"""Competitor ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(255))

    # Tracking configuration
    track_website: Mapped[bool] = mapped_column(default=True)
    track_news: Mapped[bool] = mapped_column(default=True)
    track_jobs: Mapped[bool] = mapped_column(default=True)
    track_reviews: Mapped[bool] = mapped_column(default=True)
    track_social: Mapped[bool] = mapped_column(default=True)

    # Social media links
    social_links: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # Crawl metadata
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="competitors")
    snapshots = relationship(
        "Snapshot", back_populates="competitor", cascade="all, delete-orphan"
    )
    changes = relationship(
        "Change", back_populates="competitor", cascade="all, delete-orphan"
    )
    news_items = relationship(
        "NewsItem", back_populates="competitor", cascade="all, delete-orphan"
    )
    job_postings = relationship(
        "JobPosting", back_populates="competitor", cascade="all, delete-orphan"
    )
    reviews = relationship(
        "Review", back_populates="competitor", cascade="all, delete-orphan"
    )
    social_posts = relationship(
        "SocialPost", back_populates="competitor", cascade="all, delete-orphan"
    )
    insights = relationship(
        "Insight", back_populates="competitor", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Competitor {self.name} ({self.domain})>"
