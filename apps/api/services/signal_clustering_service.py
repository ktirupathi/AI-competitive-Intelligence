"""Signal clustering service for grouping related competitive signals.

Collects recent signals from all sources (news, reviews, social posts,
website changes, job postings), generates embeddings, and clusters them
into coherent strategic themes using vector similarity + LLM labelling.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models.change import Change
from ..models.job_posting import JobPosting
from ..models.news import NewsItem
from ..models.review import Review
from ..models.social_post import SocialPost
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)
settings = get_settings()


class SignalClusteringService:
    """Group related competitive signals into meaningful clusters."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.embedding_service = EmbeddingService(db)
        self.anthropic_client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key
        )

    async def collect_recent_signals(
        self,
        competitor_ids: list[uuid.UUID],
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """Gather all recent signals across source types for given competitors.

        Returns a flat list of signal dicts, each with:
            source_type, source_id, competitor_id, text, metadata
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        signals: list[dict[str, Any]] = []

        # News items
        result = await self.db.execute(
            select(NewsItem)
            .where(
                NewsItem.competitor_id.in_(competitor_ids),
                NewsItem.discovered_at >= since,
            )
            .order_by(NewsItem.relevance_score.desc())
            .limit(100)
        )
        for item in result.scalars().all():
            signals.append({
                "source_type": "news_item",
                "source_id": item.id,
                "competitor_id": item.competitor_id,
                "text": f"{item.title}. {item.summary or ''}".strip(),
                "metadata": {
                    "title": item.title,
                    "source": item.source,
                    "sentiment": item.sentiment,
                    "relevance_score": item.relevance_score,
                },
            })

        # Website changes
        result = await self.db.execute(
            select(Change)
            .where(
                Change.competitor_id.in_(competitor_ids),
                Change.detected_at >= since,
            )
            .order_by(Change.significance_score.desc())
            .limit(100)
        )
        for item in result.scalars().all():
            signals.append({
                "source_type": "change",
                "source_id": item.id,
                "competitor_id": item.competitor_id,
                "text": f"{item.title}. {item.summary or ''}".strip(),
                "metadata": {
                    "change_type": item.change_type,
                    "severity": item.severity,
                    "significance_score": item.significance_score,
                    "page_url": item.page_url,
                },
            })

        # Job postings
        result = await self.db.execute(
            select(JobPosting)
            .where(
                JobPosting.competitor_id.in_(competitor_ids),
                JobPosting.discovered_at >= since,
                JobPosting.is_active.is_(True),
            )
            .limit(100)
        )
        for item in result.scalars().all():
            text_parts = [item.title]
            if item.department:
                text_parts.append(f"Department: {item.department}")
            if item.location:
                text_parts.append(f"Location: {item.location}")
            signals.append({
                "source_type": "job_posting",
                "source_id": item.id,
                "competitor_id": item.competitor_id,
                "text": ". ".join(text_parts),
                "metadata": {
                    "title": item.title,
                    "department": item.department,
                    "seniority_level": item.seniority_level,
                },
            })

        # Reviews
        result = await self.db.execute(
            select(Review)
            .where(
                Review.competitor_id.in_(competitor_ids),
                Review.discovered_at >= since,
            )
            .limit(50)
        )
        for item in result.scalars().all():
            text = f"{item.title or 'Review'}. {item.body or ''}"
            if item.pros:
                text += f" Pros: {item.pros}"
            if item.cons:
                text += f" Cons: {item.cons}"
            signals.append({
                "source_type": "review",
                "source_id": item.id,
                "competitor_id": item.competitor_id,
                "text": text[:1000],
                "metadata": {
                    "platform": item.platform,
                    "rating": item.rating,
                    "sentiment": item.sentiment,
                },
            })

        # Social posts
        result = await self.db.execute(
            select(SocialPost)
            .where(
                SocialPost.competitor_id.in_(competitor_ids),
                SocialPost.discovered_at >= since,
            )
            .limit(100)
        )
        for item in result.scalars().all():
            signals.append({
                "source_type": "social_post",
                "source_id": item.id,
                "competitor_id": item.competitor_id,
                "text": (item.content or "")[:1000],
                "metadata": {
                    "platform": item.platform,
                    "likes": item.likes,
                    "sentiment": item.sentiment,
                    "topics": item.topics,
                },
            })

        logger.info(
            "Collected %d signals from %d competitors (last %d days)",
            len(signals), len(competitor_ids), days,
        )
        return signals

    async def cluster_signals(
        self,
        signals: list[dict[str, Any]],
        max_clusters: int = 10,
    ) -> list[dict[str, Any]]:
        """Cluster signals into coherent themes using LLM analysis.

        Returns a list of cluster dicts with:
            cluster_title, cluster_description, confidence_score,
            impact_score, related_signals (list of signal indices)
        """
        if len(signals) < 2:
            return []

        # Prepare signal summaries for the LLM
        signal_summaries = []
        for i, sig in enumerate(signals[:80]):  # Cap to avoid token limits
            signal_summaries.append(
                f"[{i}] ({sig['source_type']}) {sig['text'][:200]}"
            )

        prompt = (
            "You are a competitive intelligence analyst. Group these signals "
            "into thematic clusters that reveal strategic patterns.\n\n"
            "SIGNALS:\n" + "\n".join(signal_summaries) + "\n\n"
            "Return ONLY valid JSON (no markdown fences) with this schema:\n"
            "[\n"
            "  {\n"
            '    "cluster_title": "Short descriptive title",\n'
            '    "cluster_description": "2-3 sentence explanation of the pattern",\n'
            '    "confidence_score": 0.0 to 1.0,\n'
            '    "impact_score": 0.0 to 1.0,\n'
            '    "related_signal_indices": [0, 3, 7]\n'
            "  }\n"
            "]\n\n"
            "Guidelines:\n"
            f"- Create {min(max_clusters, len(signals) // 2)} clusters maximum\n"
            "- Each signal should appear in at most one cluster\n"
            "- Only create clusters with 2+ related signals\n"
            "- confidence_score: how certain the connection is\n"
            "- impact_score: potential business impact of the pattern\n"
            "- Ignore noise signals that don't fit any pattern"
        )

        try:
            response = await self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                lines = [ln for ln in lines if not ln.strip().startswith("```")]
                raw = "\n".join(lines)
            clusters_raw = json.loads(raw)
        except (json.JSONDecodeError, anthropic.APIError) as exc:
            logger.error("Signal clustering LLM call failed: %s", exc)
            return []

        # Validate and enrich clusters
        clusters: list[dict[str, Any]] = []
        for c in clusters_raw:
            if not isinstance(c, dict):
                continue
            indices = c.get("related_signal_indices", [])
            related = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(signals):
                    related.append(signals[idx])
            if len(related) < 2:
                continue

            clusters.append({
                "cluster_title": str(c.get("cluster_title", "Unnamed Cluster")),
                "cluster_description": str(c.get("cluster_description", "")),
                "confidence_score": _clamp(c.get("confidence_score", 0.5)),
                "impact_score": _clamp(c.get("impact_score", 0.5)),
                "related_signals": related,
            })

        # Sort by impact
        clusters.sort(key=lambda x: x["impact_score"], reverse=True)

        logger.info("Clustered %d signals into %d clusters", len(signals), len(clusters))
        return clusters

    async def score_cluster_significance(
        self,
        cluster: dict[str, Any],
    ) -> dict[str, Any]:
        """Compute an aggregate significance score for a cluster.

        Combines the LLM-assigned scores with signal-level metadata.
        """
        related = cluster.get("related_signals", [])
        if not related:
            return cluster

        # Average significance from underlying signals
        sig_scores = []
        for sig in related:
            meta = sig.get("metadata", {})
            score = meta.get("significance_score") or meta.get("relevance_score")
            if score is not None:
                sig_scores.append(float(score))

        avg_signal_score = sum(sig_scores) / len(sig_scores) if sig_scores else 0.5

        # Blend LLM score with signal-level evidence
        llm_impact = cluster.get("impact_score", 0.5)
        blended = (llm_impact * 0.6) + (avg_signal_score * 0.4)
        cluster["impact_score"] = round(min(1.0, blended), 3)

        # Boost if many source types are represented (cross-signal correlation)
        source_types = {s["source_type"] for s in related}
        if len(source_types) >= 3:
            cluster["confidence_score"] = min(
                1.0, cluster.get("confidence_score", 0.5) + 0.1
            )

        return cluster


def _clamp(value: Any, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return 0.5
