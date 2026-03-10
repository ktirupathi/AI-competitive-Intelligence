"""
Scout AI - News Agent

Searches for competitor news and press mentions via web search APIs,
then uses Claude to extract relevance, sentiment, and summaries.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import anthropic
import httpx

from agents.config import settings
from agents.prompts import NEWS_ANALYSIS_SYSTEM, NEWS_ANALYSIS_USER
from agents.state import NewsItem, PipelineState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Web search helpers
# ---------------------------------------------------------------------------


async def _search_serper(
    query: str, client: httpx.AsyncClient, num_results: int = 10
) -> List[Dict[str, Any]]:
    """Search via Serper.dev Google Search API."""
    resp = await client.post(
        f"{settings.web_search.serper_base_url}/search",
        json={"q": query, "num": num_results},
        headers={
            "X-API-KEY": settings.web_search.api_key,
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    results = []
    for item in data.get("organic", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", ""),
            "source": item.get("source", ""),
            "date": item.get("date"),
        })
    # Include news results if present
    for item in data.get("news", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", ""),
            "source": item.get("source", ""),
            "date": item.get("date"),
        })
    return results


async def _search_provider(
    query: str, client: httpx.AsyncClient
) -> List[Dict[str, Any]]:
    """Dispatch to the configured search provider."""
    if settings.web_search.provider == "serper":
        return await _search_serper(query, client, settings.web_search.max_results)
    # Default / fallback: serper
    return await _search_serper(query, client, settings.web_search.max_results)


# ---------------------------------------------------------------------------
# Claude analysis
# ---------------------------------------------------------------------------


async def _analyse_news_item(
    competitor_name: str,
    watch_keywords: List[str],
    title: str,
    source: str,
    snippet: str,
) -> Dict[str, Any]:
    """Use Claude Haiku to score and summarise a news item."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic.api_key)

    user_msg = NEWS_ANALYSIS_USER.format(
        competitor_name=competitor_name,
        watch_keywords=", ".join(watch_keywords),
        title=title,
        source=source,
        snippet=snippet,
    )

    try:
        response = await client.messages.create(
            model=settings.anthropic.classification_model,
            max_tokens=settings.anthropic.max_tokens_classification,
            temperature=settings.anthropic.temperature_classification,
            system=NEWS_ANALYSIS_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        return json.loads(response.content[0].text.strip())
    except (json.JSONDecodeError, IndexError, anthropic.APIError) as exc:
        logger.error("News analysis failed for '%s': %s", title, exc)
        return {
            "summary": snippet[:200],
            "relevance_score": 0.3,
            "sentiment": "neutral",
            "key_topics": [],
        }


# ---------------------------------------------------------------------------
# Core agent function
# ---------------------------------------------------------------------------


async def news_agent(state: PipelineState) -> PipelineState:
    """
    LangGraph node: search for competitor news, analyse relevance & sentiment.

    Reads:
        state["competitors"]
    Writes:
        state["news_items"]
    """
    competitors = state.get("competitors", [])
    errors: List[Dict[str, Any]] = list(state.get("errors", []))
    all_news: List[NewsItem] = []

    async with httpx.AsyncClient() as http_client:
        sem = asyncio.Semaphore(settings.pipeline.max_concurrent_competitors)

        async def _process_competitor(comp: Dict[str, Any]) -> None:
            async with sem:
                name = comp["name"]
                keywords = comp.get("watch_keywords", [])

                # Build search queries
                queries = [
                    f'"{name}" company news',
                    f'"{name}" product launch OR funding OR acquisition',
                ]
                if keywords:
                    queries.append(f'"{name}" {" OR ".join(keywords[:5])}')

                raw_results: List[Dict[str, Any]] = []
                for query in queries:
                    try:
                        results = await _search_provider(query, http_client)
                        raw_results.extend(results)
                    except Exception as exc:
                        logger.error("Search failed for query '%s': %s", query, exc)
                        errors.append({
                            "agent": "news",
                            "query": query,
                            "error": str(exc),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })

                # Deduplicate by URL
                seen_urls: set = set()
                unique_results: List[Dict[str, Any]] = []
                for r in raw_results:
                    if r["url"] not in seen_urls:
                        seen_urls.add(r["url"])
                        unique_results.append(r)

                # Analyse each result with Claude
                for result in unique_results[:settings.web_search.max_results]:
                    try:
                        analysis = await _analyse_news_item(
                            competitor_name=name,
                            watch_keywords=keywords,
                            title=result["title"],
                            source=result.get("source", "unknown"),
                            snippet=result.get("snippet", ""),
                        )

                        news_item: NewsItem = {
                            "competitor_name": name,
                            "title": result["title"],
                            "url": result["url"],
                            "source": result.get("source", "unknown"),
                            "published_at": result.get("date"),
                            "summary": analysis.get("summary", ""),
                            "relevance_score": float(analysis.get("relevance_score", 0.3)),
                            "sentiment": analysis.get("sentiment", "neutral"),
                            "raw_snippet": result.get("snippet", ""),
                        }
                        all_news.append(news_item)
                    except Exception as exc:
                        logger.error(
                            "News item analysis failed for '%s': %s",
                            result["title"],
                            exc,
                        )
                        errors.append({
                            "agent": "news",
                            "title": result["title"],
                            "error": str(exc),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })

        await asyncio.gather(
            *[_process_competitor(comp) for comp in competitors]
        )

    # Sort by relevance, highest first
    all_news.sort(key=lambda n: n["relevance_score"], reverse=True)

    logger.info("News agent complete: %d items collected", len(all_news))

    return {
        "news_items": all_news,
        "errors": errors,
    }
