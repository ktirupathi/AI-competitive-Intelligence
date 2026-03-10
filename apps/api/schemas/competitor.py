"""Pydantic schemas for competitors."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class CompetitorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    domain: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    logo_url: str | None = None
    industry: str | None = None
    track_website: bool = True
    track_news: bool = True
    track_jobs: bool = True
    track_reviews: bool = True
    track_social: bool = True
    social_links: dict | None = None


class CompetitorCreate(CompetitorBase):
    pass


class CompetitorUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    domain: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    logo_url: str | None = None
    industry: str | None = None
    track_website: bool | None = None
    track_news: bool | None = None
    track_jobs: bool | None = None
    track_reviews: bool | None = None
    track_social: bool | None = None
    social_links: dict | None = None


class CompetitorRead(CompetitorBase):
    id: uuid.UUID
    user_id: uuid.UUID
    last_crawled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompetitorListResponse(BaseModel):
    items: list[CompetitorRead]
    total: int


class CompetitorDetail(CompetitorRead):
    """Extended competitor with recent activity counts."""
    recent_changes_count: int = 0
    recent_news_count: int = 0
    active_job_count: int = 0
    recent_insights_count: int = 0


class ChangeRead(BaseModel):
    id: uuid.UUID
    competitor_id: uuid.UUID
    change_type: str
    severity: str
    significance_score: float
    title: str
    summary: str | None = None
    diff_detail: dict | None = None
    page_url: str | None = None
    detected_at: datetime

    model_config = {"from_attributes": True}


class NewsItemRead(BaseModel):
    id: uuid.UUID
    competitor_id: uuid.UUID
    title: str
    url: str
    source: str | None = None
    summary: str | None = None
    sentiment: str | None = None
    relevance_score: float
    published_at: datetime | None = None
    discovered_at: datetime

    model_config = {"from_attributes": True}


class JobPostingRead(BaseModel):
    id: uuid.UUID
    competitor_id: uuid.UUID
    title: str
    url: str
    department: str | None = None
    location: str | None = None
    employment_type: str | None = None
    seniority_level: str | None = None
    skills: list | None = None
    is_active: bool
    posted_at: datetime | None = None
    discovered_at: datetime

    model_config = {"from_attributes": True}


class ReviewRead(BaseModel):
    id: uuid.UUID
    competitor_id: uuid.UUID
    platform: str
    reviewer_name: str | None = None
    rating: float | None = None
    star_rating: int | None = None
    title: str | None = None
    body: str | None = None
    sentiment: str | None = None
    reviewed_at: datetime | None = None

    model_config = {"from_attributes": True}


class SocialPostRead(BaseModel):
    id: uuid.UUID
    competitor_id: uuid.UUID
    platform: str
    url: str | None = None
    content: str | None = None
    likes: int
    shares: int
    comments_count: int
    engagement_rate: float | None = None
    posted_at: datetime | None = None

    model_config = {"from_attributes": True}
