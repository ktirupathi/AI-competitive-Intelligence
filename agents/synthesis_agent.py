"""
Scout AI - Synthesis Agent

Correlates signals from all collection agents, generates strategic insights
with scored impact and confidence, produces predictive signals and
recommended plays. Outputs a structured briefing JSON.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import anthropic

from agents.config import settings
from agents.prompts import SYNTHESIS_SYSTEM, SYNTHESIS_USER
from agents.state import (
    Briefing,
    CompetitorSummary,
    Insight,
    PipelineState,
    PredictiveSignal,
    RecommendedPlay,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_json(obj: Any, max_chars: int = 15000) -> str:
    """Serialise an object to a truncated JSON string for prompt injection."""
    try:
        raw = json.dumps(obj, indent=2, default=str)
    except (TypeError, ValueError):
        raw = str(obj)
    if len(raw) > max_chars:
        return raw[:max_chars] + "\n... [truncated]"
    return raw


def _empty_briefing() -> Briefing:
    """Return a valid but empty briefing skeleton."""
    return {
        "executive_summary": "Insufficient data to generate a briefing.",
        "top_insights": [],
        "predictive_signals": [],
        "recommended_plays": [],
        "competitor_summaries": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _validate_and_normalise(raw: Dict[str, Any], competitors: List[Dict[str, Any]]) -> Briefing:
    """
    Validate the raw JSON from Claude and coerce it into the Briefing schema,
    filling in defaults for any missing or malformed fields.
    """
    now = datetime.now(timezone.utc).isoformat()

    # --- Executive summary ---
    executive_summary = raw.get("executive_summary", "")
    if not isinstance(executive_summary, str) or not executive_summary:
        executive_summary = "No executive summary generated."

    # --- Insights ---
    top_insights: List[Insight] = []
    for item in raw.get("top_insights", []):
        if not isinstance(item, dict):
            continue
        top_insights.append({
            "title": str(item.get("title", "Untitled")),
            "description": str(item.get("description", "")),
            "impact_score": _clamp(item.get("impact_score", 0.5)),
            "confidence_score": _clamp(item.get("confidence_score", 0.5)),
            "category": str(item.get("category", "strategy")),
            "sources": [str(s) for s in item.get("sources", [])],
        })
    # Sort by impact descending
    top_insights.sort(key=lambda i: i["impact_score"], reverse=True)

    # --- Predictive signals ---
    predictive_signals: List[PredictiveSignal] = []
    for item in raw.get("predictive_signals", []):
        if not isinstance(item, dict):
            continue
        predictive_signals.append({
            "signal": str(item.get("signal", "")),
            "confidence": _clamp(item.get("confidence", 0.5)),
            "timeframe": str(item.get("timeframe", "unknown")),
            "evidence": [str(e) for e in item.get("evidence", [])],
        })

    # --- Recommended plays ---
    recommended_plays: List[RecommendedPlay] = []
    valid_priorities = {"high", "medium", "low"}
    for item in raw.get("recommended_plays", []):
        if not isinstance(item, dict):
            continue
        priority = str(item.get("priority", "medium")).lower()
        if priority not in valid_priorities:
            priority = "medium"
        recommended_plays.append({
            "action": str(item.get("action", "")),
            "rationale": str(item.get("rationale", "")),
            "priority": priority,
            "effort": str(item.get("effort", "medium")),
        })

    # --- Competitor summaries ---
    competitor_summaries: List[CompetitorSummary] = []
    raw_summaries = {
        cs.get("name", "").lower(): cs
        for cs in raw.get("competitor_summaries", [])
        if isinstance(cs, dict)
    }
    valid_threat_levels = {"low", "moderate", "high", "critical"}
    for comp in competitors:
        name = comp["name"]
        cs = raw_summaries.get(name.lower(), {})
        threat = str(cs.get("threat_level", "low")).lower()
        if threat not in valid_threat_levels:
            threat = "low"
        competitor_summaries.append({
            "name": name,
            "domain": comp["domain"],
            "key_changes": [str(c) for c in cs.get("key_changes", [])],
            "threat_level": threat,
        })

    return {
        "executive_summary": executive_summary,
        "top_insights": top_insights,
        "predictive_signals": predictive_signals,
        "recommended_plays": recommended_plays,
        "competitor_summaries": competitor_summaries,
        "generated_at": now,
    }


def _clamp(value: Any, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a value to [lo, hi], coercing to float."""
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return 0.5


# ---------------------------------------------------------------------------
# Core agent function
# ---------------------------------------------------------------------------


async def synthesis_agent(state: PipelineState) -> PipelineState:
    """
    LangGraph node: synthesise all collected signals into a strategic briefing.

    Pipeline: signals -> clustering -> predictions -> insight generation -> briefing

    Reads:
        state["competitors"], state["changes"], state["news_items"],
        state["job_postings"], state["reviews"], state["social_posts"],
        state["signal_clusters"], state["predictions"]
    Writes:
        state["insights"], state["briefing"]
    """
    competitors = state.get("competitors", [])
    changes = state.get("changes", [])
    news_items = state.get("news_items", [])
    job_postings = state.get("job_postings", [])
    reviews = state.get("reviews", [])
    social_posts = state.get("social_posts", [])
    signal_clusters = state.get("signal_clusters", [])
    predictions = state.get("predictions", [])
    errors: List[Dict[str, Any]] = list(state.get("errors", []))

    # Check if we have any signals at all
    total_signals = len(changes) + len(news_items) + len(job_postings) + len(reviews) + len(social_posts)
    if total_signals == 0:
        logger.warning("No signals collected — returning empty briefing")
        return {
            "insights": [],
            "briefing": _empty_briefing(),
            "errors": errors,
        }

    # Build the synthesis prompt with clustering and prediction context
    user_msg = SYNTHESIS_USER.format(
        changes_json=_safe_json(changes),
        news_json=_safe_json(news_items),
        jobs_json=_safe_json(job_postings),
        reviews_json=_safe_json(reviews),
        social_json=_safe_json(social_posts),
        clusters_json=_safe_json(signal_clusters) if signal_clusters else "No clusters generated.",
        predictions_json=_safe_json(predictions) if predictions else "No predictions generated.",
        competitors_json=_safe_json(competitors),
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic.api_key)

    try:
        response = await client.messages.create(
            model=settings.anthropic.synthesis_model,
            max_tokens=settings.anthropic.max_tokens_synthesis,
            temperature=settings.anthropic.temperature_synthesis,
            system=SYNTHESIS_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw_text = response.content[0].text.strip()

        # Strip markdown fences if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            # Remove first and last fence lines
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw_text = "\n".join(lines)

        raw_json = json.loads(raw_text)
        briefing = _validate_and_normalise(raw_json, competitors)

        logger.info(
            "Synthesis complete: %d insights, %d predictions, %d plays",
            len(briefing["top_insights"]),
            len(briefing["predictive_signals"]),
            len(briefing["recommended_plays"]),
        )

        return {
            "insights": briefing["top_insights"],
            "briefing": briefing,
            "errors": errors,
        }

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse synthesis JSON: %s", exc)
        errors.append({
            "agent": "synthesis",
            "error": f"JSON parse error: {exc}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "insights": [],
            "briefing": _empty_briefing(),
            "errors": errors,
        }

    except anthropic.APIError as exc:
        logger.error("Anthropic API error during synthesis: %s", exc)
        errors.append({
            "agent": "synthesis",
            "error": f"API error: {exc}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "insights": [],
            "briefing": _empty_briefing(),
            "errors": errors,
        }

    except Exception as exc:
        logger.error("Unexpected synthesis error: %s", exc, exc_info=True)
        errors.append({
            "agent": "synthesis",
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "insights": [],
            "briefing": _empty_briefing(),
            "errors": errors,
        }
