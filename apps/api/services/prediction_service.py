"""Prediction engine for forecasting competitor strategy.

Uses clustered signals and historical patterns to generate predictions
about competitor moves, timelines, and confidence levels via LLM reasoning.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PredictionService:
    """Predict competitor strategy based on clustered signals."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.anthropic_client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key
        )

    async def generate_predictions(
        self,
        clusters: list[dict[str, Any]],
        competitor_names: list[str] | None = None,
        max_predictions: int = 7,
    ) -> list[dict[str, Any]]:
        """Generate strategic predictions from signal clusters.

        Args:
            clusters: Output from SignalClusteringService.cluster_signals()
            competitor_names: List of competitor names for context
            max_predictions: Maximum number of predictions to generate

        Returns:
            List of prediction dicts with:
                prediction, confidence, timeline, evidence,
                competitor, category
        """
        if not clusters:
            return []

        # Build context from clusters
        cluster_summaries = []
        for i, cluster in enumerate(clusters):
            signals_summary = []
            for sig in cluster.get("related_signals", [])[:5]:
                signals_summary.append(
                    f"  - ({sig['source_type']}) {sig['text'][:150]}"
                )
            cluster_summaries.append(
                f"Cluster {i + 1}: {cluster['cluster_title']}\n"
                f"Description: {cluster['cluster_description']}\n"
                f"Impact: {cluster['impact_score']:.0%} | "
                f"Confidence: {cluster['confidence_score']:.0%}\n"
                f"Evidence:\n" + "\n".join(signals_summary)
            )

        competitors_str = ", ".join(competitor_names) if competitor_names else "monitored competitors"

        prompt = (
            "You are a competitive intelligence strategist. Based on the "
            "following signal clusters detected from monitoring "
            f"{competitors_str}, generate strategic predictions.\n\n"
            + "\n\n".join(cluster_summaries)
            + "\n\n"
            "Return ONLY valid JSON (no markdown fences) as an array:\n"
            "[\n"
            "  {\n"
            '    "prediction": "Clear statement of what will happen",\n'
            '    "confidence": 0.0 to 1.0,\n'
            '    "timeline": "e.g. next 30 days, Q2 2026, within 60 days",\n'
            '    "evidence": ["evidence point 1", "evidence point 2"],\n'
            '    "competitor": "company name or null if industry-wide",\n'
            '    "category": "product_launch | pricing_change | market_expansion | '
            'talent_strategy | partnership | acquisition | feature_development | other"\n'
            "  }\n"
            "]\n\n"
            "Guidelines:\n"
            f"- Generate up to {max_predictions} predictions\n"
            "- Only predict where evidence supports it\n"
            "- Confidence should reflect evidence strength:\n"
            "  0.3-0.5: speculative but plausible\n"
            "  0.5-0.7: reasonable inference from multiple signals\n"
            "  0.7-0.9: strong evidence from correlated signals\n"
            "  0.9+: near-certain based on direct announcements\n"
            "- Timelines should be specific (not vague)\n"
            "- Evidence should reference specific signals\n"
            "- Be bold but calibrated — this is for strategic planning"
        )

        try:
            response = await self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                lines = [ln for ln in lines if not ln.strip().startswith("```")]
                raw = "\n".join(lines)
            predictions_raw = json.loads(raw)
        except (json.JSONDecodeError, anthropic.APIError) as exc:
            logger.error("Prediction generation failed: %s", exc)
            return []

        # Validate predictions
        predictions: list[dict[str, Any]] = []
        for p in predictions_raw:
            if not isinstance(p, dict):
                continue
            predictions.append({
                "prediction": str(p.get("prediction", "")),
                "confidence": _clamp(p.get("confidence", 0.5)),
                "timeline": str(p.get("timeline", "unknown")),
                "evidence": [str(e) for e in p.get("evidence", [])],
                "competitor": p.get("competitor"),
                "category": str(p.get("category", "other")),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })

        # Sort by confidence descending
        predictions.sort(key=lambda x: x["confidence"], reverse=True)

        logger.info("Generated %d predictions from %d clusters", len(predictions), len(clusters))
        return predictions[:max_predictions]


def _clamp(value: Any, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return 0.5
