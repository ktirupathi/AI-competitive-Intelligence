"""
Scout AI - Main LangGraph Pipeline

Orchestrates the full competitive-intelligence workflow:

    collect signals  ->  cluster signals  ->  generate predictions
                     ->  synthesise       ->  generate briefing
                     ->  deliver

Collection agents (web_monitor, news, jobs, reviews, social) run in
parallel fan-out.  Clustering, prediction, synthesis, and delivery
run sequentially afterwards.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph

from agents.config import settings
from agents.delivery_agent import delivery_agent
from agents.job_agent import job_agent
from agents.news_agent import news_agent
from agents.review_agent import review_agent
from agents.social_agent import social_agent
from agents.state import PipelineState
from agents.synthesis_agent import synthesis_agent
from agents.web_monitor_agent import web_monitor_agent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Wrapper nodes that merge parallel results into the shared state
# ---------------------------------------------------------------------------
# LangGraph calls each node with the full state and expects a partial state
# dict back.  The wrappers below are thin async shims that call the real
# agent functions and handle retries.


async def _with_retries(fn, state: PipelineState, agent_name: str) -> PipelineState:
    """Execute an agent function with configurable retry logic."""
    max_retries = settings.pipeline.agent_max_retries
    delay = settings.pipeline.agent_retry_delay_seconds

    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            return await fn(state)
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "%s failed (attempt %d/%d): %s",
                agent_name,
                attempt,
                max_retries,
                exc,
            )
            if attempt < max_retries:
                await asyncio.sleep(delay * attempt)

    # All retries exhausted — return error info without crashing pipeline
    logger.error("%s failed after %d attempts: %s", agent_name, max_retries, last_exc)
    return {
        "errors": list(state.get("errors", [])) + [
            {
                "agent": agent_name,
                "error": str(last_exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }


# --- Node functions (must be sync for LangGraph; they return coroutines via asyncio.run) ---
# LangGraph StateGraph natively supports async node functions, so we keep them async.

async def node_web_monitor(state: PipelineState) -> PipelineState:
    return await _with_retries(web_monitor_agent, state, "web_monitor")


async def node_news(state: PipelineState) -> PipelineState:
    return await _with_retries(news_agent, state, "news")


async def node_jobs(state: PipelineState) -> PipelineState:
    return await _with_retries(job_agent, state, "job")


async def node_reviews(state: PipelineState) -> PipelineState:
    return await _with_retries(review_agent, state, "review")


async def node_social(state: PipelineState) -> PipelineState:
    return await _with_retries(social_agent, state, "social")


async def node_cluster_signals(state: PipelineState) -> PipelineState:
    """Cluster related signals from all collection agents."""
    return await _cluster_and_predict(state, phase="cluster")


async def node_predict(state: PipelineState) -> PipelineState:
    """Generate predictions from clustered signals."""
    return await _cluster_and_predict(state, phase="predict")


async def _cluster_and_predict(state: PipelineState, phase: str) -> PipelineState:
    """Run clustering or prediction in-process (no separate agent module needed).

    This uses the pipeline's collected data to build lightweight signal
    representations, then calls Claude for clustering and prediction.
    """
    import json

    import anthropic

    errors: list = list(state.get("errors", []))
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic.api_key)

    if phase == "cluster":
        # Build signal summaries from all sources
        signal_texts: list[str] = []
        for c in state.get("changes", []):
            signal_texts.append(f"(website_change) {c.get('diff_summary', c.get('change_category', ''))} [{c.get('significance', 'medium')}]")
        for n in state.get("news_items", []):
            signal_texts.append(f"(news) {n.get('title', '')}. {n.get('summary', '')}")
        for j in state.get("job_postings", []):
            signal_texts.append(f"(job) {j.get('title', '')} - {j.get('department', '')} [{j.get('seniority', '')}]")
        for r in state.get("reviews", []):
            signal_texts.append(f"(review) {r.get('title', '')} - pros: {r.get('pros', '')} cons: {r.get('cons', '')}")
        for s in state.get("social_posts", []):
            signal_texts.append(f"(social/{s.get('platform', '')}) {s.get('content', '')[:150]}")

        if len(signal_texts) < 3:
            return {"signal_clusters": [], "errors": errors}

        numbered = [f"[{i}] {t}" for i, t in enumerate(signal_texts[:60])]
        prompt = (
            "Group these competitive intelligence signals into thematic clusters.\n\n"
            "SIGNALS:\n" + "\n".join(numbered) + "\n\n"
            "Return ONLY valid JSON array (no fences):\n"
            '[{"cluster_title":"...","cluster_description":"...","confidence_score":0.7,'
            '"impact_score":0.8,"related_signal_indices":[0,3,7]}]\n'
            "Rules: 2+ signals per cluster, max 8 clusters, skip noise signals."
        )
        try:
            resp = await client.messages.create(
                model=settings.anthropic.synthesis_model,
                max_tokens=4096,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                lines = [ln for ln in lines if not ln.strip().startswith("```")]
                raw = "\n".join(lines)
            clusters_raw = json.loads(raw)

            clusters = []
            for c in clusters_raw:
                if not isinstance(c, dict):
                    continue
                indices = c.get("related_signal_indices", [])
                related = []
                for idx in indices:
                    if isinstance(idx, int) and 0 <= idx < len(signal_texts):
                        related.append({"index": idx, "text": signal_texts[idx]})
                if len(related) >= 2:
                    clusters.append({
                        "cluster_title": str(c.get("cluster_title", "")),
                        "cluster_description": str(c.get("cluster_description", "")),
                        "confidence_score": max(0.0, min(1.0, float(c.get("confidence_score", 0.5)))),
                        "impact_score": max(0.0, min(1.0, float(c.get("impact_score", 0.5)))),
                        "related_signals": related,
                    })
            clusters.sort(key=lambda x: x["impact_score"], reverse=True)
            logger.info("Clustered %d signals into %d clusters", len(signal_texts), len(clusters))
            return {"signal_clusters": clusters, "errors": errors}
        except Exception as exc:
            logger.error("Signal clustering failed: %s", exc)
            errors.append({"agent": "clustering", "error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()})
            return {"signal_clusters": [], "errors": errors}

    else:  # predict
        clusters = state.get("signal_clusters", [])
        if not clusters:
            return {"predictions": [], "errors": errors}

        cluster_summaries = []
        for i, cl in enumerate(clusters[:8]):
            sigs = [s.get("text", "") for s in cl.get("related_signals", [])[:4]]
            cluster_summaries.append(
                f"Cluster {i+1}: {cl['cluster_title']}\n"
                f"  {cl['cluster_description']}\n"
                f"  Impact: {cl['impact_score']:.0%}, Confidence: {cl['confidence_score']:.0%}\n"
                f"  Signals: {'; '.join(sigs)}"
            )

        comp_names = [c["name"] for c in state.get("competitors", [])]
        prompt = (
            f"Based on signal clusters for {', '.join(comp_names)}, "
            "generate strategic predictions.\n\n"
            + "\n\n".join(cluster_summaries) + "\n\n"
            "Return ONLY valid JSON array (no fences):\n"
            '[{"prediction":"...","confidence":0.7,"timeline":"next 60 days",'
            '"evidence":["..."],"competitor":"name or null","category":"product_launch|...|other"}]\n'
            "Max 5 predictions, sorted by confidence."
        )
        try:
            resp = await client.messages.create(
                model=settings.anthropic.synthesis_model,
                max_tokens=4096,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                lines = [ln for ln in lines if not ln.strip().startswith("```")]
                raw = "\n".join(lines)
            preds_raw = json.loads(raw)
            predictions = []
            for p in preds_raw:
                if not isinstance(p, dict):
                    continue
                predictions.append({
                    "prediction": str(p.get("prediction", "")),
                    "confidence": max(0.0, min(1.0, float(p.get("confidence", 0.5)))),
                    "timeline": str(p.get("timeline", "unknown")),
                    "evidence": [str(e) for e in p.get("evidence", [])],
                    "competitor": p.get("competitor"),
                    "category": str(p.get("category", "other")),
                })
            predictions.sort(key=lambda x: x["confidence"], reverse=True)
            logger.info("Generated %d predictions from %d clusters", len(predictions), len(clusters))
            return {"predictions": predictions, "errors": errors}
        except Exception as exc:
            logger.error("Prediction generation failed: %s", exc)
            errors.append({"agent": "prediction", "error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()})
            return {"predictions": [], "errors": errors}


async def node_synthesis(state: PipelineState) -> PipelineState:
    return await _with_retries(synthesis_agent, state, "synthesis")


async def node_delivery(state: PipelineState) -> PipelineState:
    return await _with_retries(delivery_agent, state, "delivery")


# ---------------------------------------------------------------------------
# Fan-out / fan-in helper
# ---------------------------------------------------------------------------

async def node_collect(state: PipelineState) -> PipelineState:
    """
    Run all five collection agents concurrently and merge their results
    into a single state update.  This is the fan-out node.
    """
    tasks = [
        _with_retries(web_monitor_agent, state, "web_monitor"),
        _with_retries(news_agent, state, "news"),
        _with_retries(job_agent, state, "job"),
        _with_retries(review_agent, state, "review"),
        _with_retries(social_agent, state, "social"),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    merged: Dict[str, Any] = {"errors": list(state.get("errors", []))}

    for res in results:
        if isinstance(res, Exception):
            logger.error("Collection task raised: %s", res)
            merged["errors"].append({
                "agent": "collect",
                "error": str(res),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            continue
        if isinstance(res, dict):
            for key, value in res.items():
                if key == "errors":
                    merged["errors"].extend(value)
                else:
                    merged[key] = value

    return merged


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def build_pipeline() -> StateGraph:
    """
    Build and return the compiled LangGraph StateGraph for the Scout AI
    competitive-intelligence pipeline.

    Graph topology:
        START -> collect -> cluster -> predict -> synthesis -> delivery -> END
    """
    graph = StateGraph(PipelineState)

    # Register nodes
    graph.add_node("collect", node_collect)
    graph.add_node("cluster", node_cluster_signals)
    graph.add_node("predict", node_predict)
    graph.add_node("synthesis", node_synthesis)
    graph.add_node("delivery", node_delivery)

    # Define edges
    graph.set_entry_point("collect")
    graph.add_edge("collect", "cluster")
    graph.add_edge("cluster", "predict")
    graph.add_edge("predict", "synthesis")
    graph.add_edge("synthesis", "delivery")
    graph.add_edge("delivery", END)

    return graph.compile()


def build_pipeline_sequential() -> StateGraph:
    """
    Alternative pipeline where each collection agent runs as a separate
    sequential node.  Useful for debugging or when API rate limits are tight.

    Graph topology:
        START -> web_monitor -> news -> jobs -> reviews -> social
              -> cluster -> predict -> synthesis -> delivery -> END
    """
    graph = StateGraph(PipelineState)

    graph.add_node("web_monitor", node_web_monitor)
    graph.add_node("news", node_news)
    graph.add_node("jobs", node_jobs)
    graph.add_node("reviews", node_reviews)
    graph.add_node("social", node_social)
    graph.add_node("cluster", node_cluster_signals)
    graph.add_node("predict", node_predict)
    graph.add_node("synthesis", node_synthesis)
    graph.add_node("delivery", node_delivery)

    graph.set_entry_point("web_monitor")
    graph.add_edge("web_monitor", "news")
    graph.add_edge("news", "jobs")
    graph.add_edge("jobs", "reviews")
    graph.add_edge("reviews", "social")
    graph.add_edge("social", "cluster")
    graph.add_edge("cluster", "predict")
    graph.add_edge("predict", "synthesis")
    graph.add_edge("synthesis", "delivery")
    graph.add_edge("delivery", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------


async def run_pipeline(
    competitors: List[Dict[str, Any]],
    *,
    user_email: Optional[str] = None,
    slack_channel: Optional[str] = None,
    webhook_url: Optional[str] = None,
    previous_snapshots: Optional[List[Dict[str, Any]]] = None,
    sequential: bool = False,
) -> PipelineState:
    """
    High-level entry point: build the graph, seed the initial state, execute,
    and return the final state.

    Parameters
    ----------
    competitors : list of CompetitorInfo dicts
    user_email : optional email address for briefing delivery
    slack_channel : optional Slack channel override
    webhook_url : optional webhook URL override
    previous_snapshots : snapshots from the last run (for change detection)
    sequential : if True, use sequential pipeline instead of parallel fan-out

    Returns
    -------
    PipelineState with all collected data, insights, briefing, and delivery results.
    """
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    initial_state: PipelineState = {
        "run_id": run_id,
        "started_at": now,
        "competitors": competitors,
        "user_email": user_email,
        "slack_channel": slack_channel,
        "webhook_url": webhook_url,
        "previous_snapshots": previous_snapshots or [],
        "snapshots": [],
        "changes": [],
        "news_items": [],
        "job_postings": [],
        "reviews": [],
        "social_posts": [],
        "signal_clusters": [],
        "predictions": [],
        "insights": [],
        "briefing": None,
        "delivery_results": [],
        "errors": [],
        "finished_at": None,
    }

    pipeline = build_pipeline_sequential() if sequential else build_pipeline()

    logger.info("Pipeline %s started (sequential=%s, competitors=%d)", run_id, sequential, len(competitors))

    final_state = await pipeline.ainvoke(initial_state)

    logger.info(
        "Pipeline %s finished: %d changes, %d news, %d jobs, %d reviews, %d social, %d insights, %d deliveries, %d errors",
        run_id,
        len(final_state.get("changes", [])),
        len(final_state.get("news_items", [])),
        len(final_state.get("job_postings", [])),
        len(final_state.get("reviews", [])),
        len(final_state.get("social_posts", [])),
        len(final_state.get("insights", [])),
        len(final_state.get("delivery_results", [])),
        len(final_state.get("errors", [])),
    )

    return final_state
