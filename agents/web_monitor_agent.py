"""
Scout AI - Web Monitor Agent

Scrapes competitor websites, detects content changes by comparing content
hashes, and classifies change significance using Claude.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import anthropic
import httpx

from agents.config import settings
from agents.prompts import CHANGE_CLASSIFICATION_SYSTEM, CHANGE_CLASSIFICATION_USER
from agents.state import ContentChange, PageSnapshot, PipelineState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scraping helpers
# ---------------------------------------------------------------------------


async def _scrape_with_firecrawl(url: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Scrape a URL via the Firecrawl API and return markdown content."""
    headers = {
        "Authorization": f"Bearer {settings.firecrawl.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
        "timeout": settings.firecrawl.timeout * 1000,
    }
    resp = await client.post(
        f"{settings.firecrawl.base_url}/scrape",
        json=payload,
        headers=headers,
        timeout=settings.firecrawl.timeout + 10,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "content": data.get("data", {}).get("markdown", ""),
        "status_code": data.get("data", {}).get("metadata", {}).get("statusCode", 200),
    }


async def _scrape_with_httpx(url: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Fallback scraper using plain httpx when Firecrawl is not configured."""
    resp = await client.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return {
        "content": resp.text,
        "status_code": resp.status_code,
    }


async def scrape_url(url: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Scrape a single URL, preferring Firecrawl, falling back to httpx."""
    if settings.firecrawl.api_key:
        try:
            return await _scrape_with_firecrawl(url, client)
        except Exception as exc:
            logger.warning("Firecrawl failed for %s, falling back to httpx: %s", url, exc)
    return await _scrape_with_httpx(url, client)


def _content_hash(text: str) -> str:
    """Produce a stable SHA-256 hex digest of normalised content."""
    normalised = " ".join(text.split()).strip().lower()
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Change classification via Claude
# ---------------------------------------------------------------------------


async def _classify_change(
    competitor_name: str,
    url: str,
    previous_content: str,
    current_content: str,
) -> Dict[str, str]:
    """Use Claude Haiku to classify a detected content change."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic.api_key)

    # Truncate content to avoid token limits
    max_chars = 3000
    prev_trunc = previous_content[:max_chars]
    curr_trunc = current_content[:max_chars]

    user_msg = CHANGE_CLASSIFICATION_USER.format(
        competitor_name=competitor_name,
        url=url,
        previous_content=prev_trunc,
        current_content=curr_trunc,
    )

    try:
        response = await client.messages.create(
            model=settings.anthropic.classification_model,
            max_tokens=settings.anthropic.max_tokens_classification,
            temperature=settings.anthropic.temperature_classification,
            system=CHANGE_CLASSIFICATION_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()
        return json.loads(raw)
    except (json.JSONDecodeError, IndexError, anthropic.APIError) as exc:
        logger.error("Change classification failed for %s: %s", url, exc)
        return {
            "diff_summary": "Classification unavailable",
            "significance": "medium",
            "change_category": "other",
            "reasoning": f"Automated classification failed: {exc}",
        }


# ---------------------------------------------------------------------------
# Core agent function
# ---------------------------------------------------------------------------


async def web_monitor_agent(state: PipelineState) -> PipelineState:
    """
    LangGraph node: scrape competitor websites, detect changes, classify them.

    Reads:
        state["competitors"], state.get("previous_snapshots")
    Writes:
        state["snapshots"], state["changes"]
    """
    competitors = state.get("competitors", [])
    previous_snapshots: List[PageSnapshot] = state.get("previous_snapshots", [])
    errors: List[Dict[str, Any]] = list(state.get("errors", []))

    # Index previous snapshots by URL for fast lookup
    prev_by_url: Dict[str, PageSnapshot] = {s["url"]: s for s in previous_snapshots}

    new_snapshots: List[PageSnapshot] = []
    changes: List[ContentChange] = []

    # Build target URL list: main domain + careers page
    targets: List[tuple[str, str]] = []  # (competitor_name, url)
    for comp in competitors:
        domain = comp["domain"].rstrip("/")
        base = f"https://{domain}" if not domain.startswith("http") else domain
        targets.append((comp["name"], base))
        targets.append((comp["name"], f"{base}/pricing"))
        targets.append((comp["name"], f"{base}/product"))
        targets.append((comp["name"], f"{base}/about"))
        if comp.get("careers_url"):
            targets.append((comp["name"], comp["careers_url"]))

    async with httpx.AsyncClient() as client:
        sem = asyncio.Semaphore(settings.pipeline.max_concurrent_competitors)

        async def _process(comp_name: str, url: str) -> None:
            async with sem:
                try:
                    result = await scrape_url(url, client)
                    content = result["content"]
                    h = _content_hash(content)
                    now = datetime.now(timezone.utc).isoformat()

                    snapshot: PageSnapshot = {
                        "url": url,
                        "content_hash": h,
                        "content_text": content[:10000],  # cap stored text
                        "fetched_at": now,
                        "status_code": result["status_code"],
                    }
                    new_snapshots.append(snapshot)

                    # Compare with previous snapshot
                    prev = prev_by_url.get(url)
                    if prev and prev["content_hash"] != h:
                        classification = await _classify_change(
                            comp_name, url, prev["content_text"], content
                        )
                        change: ContentChange = {
                            "competitor_name": comp_name,
                            "url": url,
                            "previous_hash": prev["content_hash"],
                            "current_hash": h,
                            "diff_summary": classification.get("diff_summary", ""),
                            "significance": classification.get("significance", "medium"),
                            "detected_at": now,
                            "change_category": classification.get("change_category", "other"),
                        }
                        changes.append(change)
                        logger.info(
                            "Change detected on %s [%s]: %s",
                            url,
                            change["significance"],
                            change["diff_summary"][:80],
                        )
                except Exception as exc:
                    logger.error("Failed to scrape %s: %s", url, exc)
                    errors.append({
                        "agent": "web_monitor",
                        "url": url,
                        "error": str(exc),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

        await asyncio.gather(*[_process(name, url) for name, url in targets])

    # Filter out low-significance changes if configured
    min_sig = settings.pipeline.min_change_significance
    sig_order = {"low": 0.2, "medium": 0.5, "high": 0.8, "critical": 1.0}
    filtered_changes = [
        c for c in changes if sig_order.get(c["significance"], 0.5) >= min_sig
    ]

    logger.info(
        "Web monitor complete: %d snapshots, %d changes (%d after filtering)",
        len(new_snapshots),
        len(changes),
        len(filtered_changes),
    )

    return {
        "snapshots": new_snapshots,
        "changes": filtered_changes,
        "errors": errors,
    }
