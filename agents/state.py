"""
Scout AI - LangGraph State Definitions

Typed state schema that flows through the entire competitive-intelligence
pipeline. Each agent reads from and writes to specific keys in this state.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ChangeSignificance(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PostType(str, Enum):
    ANNOUNCEMENT = "announcement"
    HIRING = "hiring"
    PRODUCT_LAUNCH = "product_launch"
    THOUGHT_LEADERSHIP = "thought_leadership"
    PARTNERSHIP = "partnership"
    EVENT = "event"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Nested data models (plain TypedDicts for LangGraph serialisation)
# ---------------------------------------------------------------------------

class CompetitorInfo(TypedDict):
    name: str
    domain: str
    careers_url: Optional[str]
    g2_slug: Optional[str]
    capterra_slug: Optional[str]
    linkedin_url: Optional[str]
    twitter_handle: Optional[str]
    watch_keywords: List[str]


class PageSnapshot(TypedDict):
    url: str
    content_hash: str
    content_text: str
    fetched_at: str  # ISO-8601
    status_code: int


class ContentChange(TypedDict):
    competitor_name: str
    url: str
    previous_hash: str
    current_hash: str
    diff_summary: str
    significance: str  # ChangeSignificance value
    detected_at: str
    change_category: str  # e.g. pricing, features, messaging


class NewsItem(TypedDict):
    competitor_name: str
    title: str
    url: str
    source: str
    published_at: Optional[str]
    summary: str
    relevance_score: float  # 0.0 - 1.0
    sentiment: str  # positive / negative / neutral
    raw_snippet: str


class JobPosting(TypedDict):
    competitor_name: str
    title: str
    department: str
    seniority: str  # junior / mid / senior / lead / exec
    location: str
    url: str
    posted_at: Optional[str]
    strategic_signal: str  # brief explanation of why this matters


class Review(TypedDict):
    competitor_name: str
    platform: str  # g2 / capterra
    rating: float
    title: str
    pros: str
    cons: str
    reviewer_role: Optional[str]
    date: Optional[str]
    sentiment: str  # positive / negative / mixed / neutral
    key_themes: List[str]


class SocialPost(TypedDict):
    competitor_name: str
    platform: str  # linkedin / twitter
    author: str
    content: str
    post_type: str  # PostType value
    url: Optional[str]
    posted_at: Optional[str]
    likes: int
    comments: int
    shares: int
    engagement_score: float


# ---------------------------------------------------------------------------
# Synthesis / briefing output models
# ---------------------------------------------------------------------------

class Insight(TypedDict):
    title: str
    description: str
    impact_score: float  # 0.0 - 1.0
    confidence_score: float  # 0.0 - 1.0
    category: str
    sources: List[str]


class SignalCluster(TypedDict):
    cluster_title: str
    cluster_description: str
    confidence_score: float
    impact_score: float
    related_signals: List[Dict[str, Any]]


class Prediction(TypedDict):
    prediction: str
    confidence: float
    timeline: str
    evidence: List[str]
    competitor: Optional[str]
    category: str


class PredictiveSignal(TypedDict):
    signal: str
    confidence: float
    timeframe: str
    evidence: List[str]


class RecommendedPlay(TypedDict):
    action: str
    rationale: str
    priority: str  # Priority value
    effort: str  # e.g. "low", "medium", "high", or descriptive


class CompetitorSummary(TypedDict):
    name: str
    domain: str
    key_changes: List[str]
    threat_level: str  # ThreatLevel value


class Briefing(TypedDict):
    executive_summary: str
    top_insights: List[Insight]
    predictive_signals: List[PredictiveSignal]
    recommended_plays: List[RecommendedPlay]
    competitor_summaries: List[CompetitorSummary]
    generated_at: str  # ISO-8601


# ---------------------------------------------------------------------------
# Delivery status
# ---------------------------------------------------------------------------

class DeliveryResult(TypedDict):
    channel: str  # email / slack / webhook
    success: bool
    message: str
    delivered_at: str


# ---------------------------------------------------------------------------
# Top-level pipeline state
# ---------------------------------------------------------------------------

class PipelineState(TypedDict, total=False):
    """
    Complete state flowing through the LangGraph pipeline.

    Keys are populated progressively as each agent executes.
    Using ``total=False`` so agents only need to return the keys they update.
    """

    # --- Input ---
    run_id: str
    started_at: str
    competitors: List[CompetitorInfo]
    user_email: Optional[str]
    slack_channel: Optional[str]
    webhook_url: Optional[str]

    # --- Web monitor ---
    snapshots: List[PageSnapshot]
    previous_snapshots: List[PageSnapshot]
    changes: List[ContentChange]

    # --- News ---
    news_items: List[NewsItem]

    # --- Jobs ---
    job_postings: List[JobPosting]

    # --- Reviews ---
    reviews: List[Review]

    # --- Social ---
    social_posts: List[SocialPost]

    # --- Clustering & Predictions ---
    signal_clusters: List[SignalCluster]
    predictions: List[Prediction]

    # --- Synthesis ---
    insights: List[Insight]
    briefing: Briefing

    # --- Delivery ---
    delivery_results: List[DeliveryResult]

    # --- Metadata ---
    errors: List[Dict[str, Any]]
    data_sources_available: List[str]
    validation_stats: Dict[str, Any]
    finished_at: Optional[str]
