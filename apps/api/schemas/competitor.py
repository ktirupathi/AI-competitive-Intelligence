"""Pydantic schemas for competitors."""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator

# Regex to strip HTML tags
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _sanitise_text(value: str, max_length: int = 200) -> str:
    """Strip HTML tags, collapse whitespace, and enforce max length."""
    value = _HTML_TAG_RE.sub("", value)
    value = " ".join(value.split())  # collapse whitespace
    return value[:max_length]


class CompetitorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    domain: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    logo_url: str | None = None
    industry: str | None = Field(None, max_length=100)
    track_website: bool = True
    track_news: bool = True
    track_jobs: bool = True
    track_reviews: bool = True
    track_social: bool = True
    social_links: dict | None = None

    @field_validator("name", mode="before")
    @classmethod
    def sanitise_name(cls, v: str) -> str:
        if isinstance(v, str):
            return _sanitise_text(v, max_length=200)
        return v

    @field_validator("domain", mode="before")
    @classmethod
    def sanitise_domain(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            # Strip trailing slashes for consistency
            v = v.rstrip("/")
        return v

    @field_validator("description", mode="before")
    @classmethod
    def sanitise_description(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return _sanitise_text(v, max_length=2000)
        return v

    @field_validator("industry", mode="before")
    @classmethod
    def sanitise_industry(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return _sanitise_text(v, max_length=100)
        return v


class CompetitorCreate(CompetitorBase):
    pass


class CompetitorUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    domain: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    logo_url: str | None = None
    industry: str | None = Field(None, max_length=100)
    track_website: bool | None = None
    track_news: bool | None = None
    track_jobs: bool | None = None
    track_reviews: bool | None = None
    track_social: bool | None = None
    social_links: dict | None = None

    @field_validator("name", mode="before")
    @classmethod
    def sanitise_name(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return _sanitise_text(v, max_length=200)
        return v

    @field_validator("description", mode="before")
    @classmethod
    def sanitise_description(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return _sanitise_text(v, max_length=2000)
        return v

    @field_validator("industry", mode="before")
    @classmethod
    def sanitise_industry(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return _sanitise_text(v, max_length=100)
        return v


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
