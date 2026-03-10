"""
Scout AI - Main LangGraph Pipeline

Orchestrates the full competitive-intelligence workflow:

    collect data  ->  detect changes  ->  score signals
                  ->  synthesise      ->  generate briefing
                  ->  deliver

Collection agents (web_monitor, news, jobs, reviews, social) run in
parallel fan-out.  Synthesis and delivery run sequentially afterwards.
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
        START -> collect -> synthesis -> delivery -> END
    """
    graph = StateGraph(PipelineState)

    # Register nodes
    graph.add_node("collect", node_collect)
    graph.add_node("synthesis", node_synthesis)
    graph.add_node("delivery", node_delivery)

    # Define edges (linear after fan-out collection)
    graph.set_entry_point("collect")
    graph.add_edge("collect", "synthesis")
    graph.add_edge("synthesis", "delivery")
    graph.add_edge("delivery", END)

    return graph.compile()


def build_pipeline_sequential() -> StateGraph:
    """
    Alternative pipeline where each collection agent runs as a separate
    sequential node.  Useful for debugging or when API rate limits are tight.

    Graph topology:
        START -> web_monitor -> news -> jobs -> reviews -> social
              -> synthesis -> delivery -> END
    """
    graph = StateGraph(PipelineState)

    graph.add_node("web_monitor", node_web_monitor)
    graph.add_node("news", node_news)
    graph.add_node("jobs", node_jobs)
    graph.add_node("reviews", node_reviews)
    graph.add_node("social", node_social)
    graph.add_node("synthesis", node_synthesis)
    graph.add_node("delivery", node_delivery)

    graph.set_entry_point("web_monitor")
    graph.add_edge("web_monitor", "news")
    graph.add_edge("news", "jobs")
    graph.add_edge("jobs", "reviews")
    graph.add_edge("reviews", "social")
    graph.add_edge("social", "synthesis")
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
