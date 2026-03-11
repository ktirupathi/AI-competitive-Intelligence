"""
Scout AI - Test Configuration & Shared Fixtures

Provides reusable fixtures for database sessions, mock API clients,
and sample data used across all test modules.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_competitor() -> dict[str, Any]:
    """A single competitor info dict matching CompetitorInfo schema."""
    return {
        "name": "Acme Corp",
        "domain": "acme.com",
        "careers_url": "https://acme.com/careers",
        "g2_slug": "acme-corp",
        "capterra_slug": "12345/acme",
        "linkedin_url": "https://www.linkedin.com/company/acme-corp",
        "twitter_handle": "@acmecorp",
        "watch_keywords": ["AI", "machine learning", "enterprise"],
    }


@pytest.fixture
def sample_competitors(sample_competitor: dict) -> list[dict[str, Any]]:
    """List of competitors for pipeline tests."""
    return [
        sample_competitor,
        {
            "name": "Globex Inc",
            "domain": "globex.io",
            "careers_url": None,
            "g2_slug": "globex",
            "capterra_slug": None,
            "linkedin_url": None,
            "twitter_handle": "@globexinc",
            "watch_keywords": ["analytics", "data"],
        },
    ]


@pytest.fixture
def sample_pipeline_state(sample_competitors: list[dict]) -> dict[str, Any]:
    """A fully populated PipelineState for synthesis/delivery testing."""
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    return {
        "run_id": run_id,
        "started_at": now,
        "competitors": sample_competitors,
        "user_email": "test@example.com",
        "slack_channel": "#test-channel",
        "webhook_url": "https://hooks.example.com/test",
        "previous_snapshots": [],
        "snapshots": [
            {
                "url": "https://acme.com",
                "content_hash": "abc123",
                "content_text": "Welcome to Acme Corp. We build great products.",
                "fetched_at": now,
                "status_code": 200,
            }
        ],
        "changes": [
            {
                "competitor_name": "Acme Corp",
                "url": "https://acme.com/pricing",
                "previous_hash": "old_hash",
                "current_hash": "new_hash",
                "diff_summary": "Pricing increased by 20%",
                "significance": "high",
                "detected_at": now,
                "change_category": "pricing",
            }
        ],
        "news_items": [
            {
                "competitor_name": "Acme Corp",
                "title": "Acme Corp raises $50M Series C",
                "url": "https://news.example.com/acme-funding",
                "source": "TechCrunch",
                "published_at": now,
                "summary": "Acme Corp announced a $50M Series C round.",
                "relevance_score": 0.9,
                "sentiment": "positive",
                "raw_snippet": "Acme Corp raises $50M...",
            }
        ],
        "job_postings": [
            {
                "competitor_name": "Acme Corp",
                "title": "Senior ML Engineer",
                "department": "engineering",
                "seniority": "senior",
                "location": "Remote",
                "url": "https://acme.com/careers",
                "posted_at": None,
                "strategic_signal": "Investing heavily in ML capabilities",
            }
        ],
        "reviews": [
            {
                "competitor_name": "Acme Corp",
                "platform": "g2",
                "rating": 4.5,
                "title": "Great product but expensive",
                "pros": "Feature-rich, reliable",
                "cons": "Expensive, steep learning curve",
                "reviewer_role": "CTO",
                "date": now,
                "sentiment": "positive",
                "key_themes": ["features", "pricing"],
            }
        ],
        "social_posts": [
            {
                "competitor_name": "Acme Corp",
                "platform": "linkedin",
                "author": "Acme Corp",
                "content": "Excited to announce our new AI feature!",
                "post_type": "product_launch",
                "url": "https://linkedin.com/posts/acme",
                "posted_at": now,
                "likes": 150,
                "comments": 25,
                "shares": 30,
                "engagement_score": 0.85,
            }
        ],
        "signal_clusters": [],
        "predictions": [],
        "insights": [],
        "briefing": None,
        "delivery_results": [],
        "errors": [],
        "finished_at": None,
    }


@pytest.fixture
def sample_briefing() -> dict[str, Any]:
    """A complete briefing dict for delivery agent testing."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "executive_summary": "Acme Corp is aggressively expanding their AI capabilities.",
        "top_insights": [
            {
                "title": "Acme investing in ML",
                "description": "Multiple hiring signals point to ML expansion.",
                "impact_score": 0.8,
                "confidence_score": 0.7,
                "category": "talent",
                "sources": ["job_postings", "social_media"],
            }
        ],
        "predictive_signals": [
            {
                "signal": "Acme likely to launch AI product within 90 days",
                "confidence": 0.75,
                "timeframe": "next 90 days",
                "evidence": ["ML hiring surge", "social media hints"],
            }
        ],
        "recommended_plays": [
            {
                "action": "Accelerate own AI feature roadmap",
                "rationale": "Acme is closing the gap quickly",
                "priority": "high",
                "effort": "high",
            }
        ],
        "competitor_summaries": [
            {
                "name": "Acme Corp",
                "domain": "acme.com",
                "key_changes": ["Pricing increase", "ML hiring"],
                "threat_level": "high",
            }
        ],
        "generated_at": now,
    }


# ---------------------------------------------------------------------------
# Mock client fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_anthropic_client() -> MagicMock:
    """Mock Anthropic client that returns a structured JSON response."""
    client = AsyncMock()
    response = MagicMock()
    response.content = [MagicMock(text='{"test": "response"}')]
    client.messages.create = AsyncMock(return_value=response)
    return client


@pytest.fixture
def mock_firecrawl_response() -> dict[str, Any]:
    """Standard successful Firecrawl response."""
    return {
        "data": {
            "markdown": "# Welcome to Acme Corp\n\nWe build enterprise software.",
            "metadata": {"statusCode": 200},
        }
    }


@pytest.fixture
def mock_serper_response() -> dict[str, Any]:
    """Standard successful Serper search response."""
    return {
        "organic": [
            {
                "title": "Acme Corp raises $50M",
                "link": "https://techcrunch.com/acme-funding",
                "snippet": "Acme Corp announced a $50M Series C funding round.",
                "source": "TechCrunch",
                "date": "2025-12-01",
            },
            {
                "title": "Acme launches new product",
                "link": "https://blog.acme.com/new-product",
                "snippet": "Acme Corp has launched a new AI-powered product.",
                "source": "Acme Blog",
                "date": "2025-11-28",
            },
        ],
        "news": [],
    }
