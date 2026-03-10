"""Scheduled competitor monitoring tasks."""

import asyncio
import hashlib
import logging
import uuid
from datetime import datetime, timezone

import anthropic
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..celery_app import celery
from ..config import get_settings
from ..database import async_session_factory
from ..models.change import Change
from ..models.competitor import Competitor
from ..models.insight import Insight
from ..models.news import NewsItem
from ..models.snapshot import Snapshot

logger = logging.getLogger(__name__)
settings = get_settings()


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery.task(name="apps.api.tasks.monitoring.run_monitoring_cycle")
def run_monitoring_cycle():
    """Run a full monitoring cycle for all active competitors."""
    logger.info("Starting monitoring cycle")
    _run_async(_monitoring_cycle())
    logger.info("Monitoring cycle complete")


@celery.task(name="apps.api.tasks.monitoring.monitor_single_competitor")
def monitor_single_competitor(competitor_id: str):
    """Monitor a single competitor on demand."""
    _run_async(_monitor_competitor(uuid.UUID(competitor_id)))


async def _monitoring_cycle():
    """Iterate all active competitors and monitor each."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Competitor).where(Competitor.user_id.isnot(None))
        )
        competitors = list(result.scalars().all())

    logger.info("Found %d competitors to monitor", len(competitors))

    for competitor in competitors:
        try:
            await _monitor_competitor(competitor.id)
        except Exception:
            logger.exception(
                "Error monitoring competitor %s (%s)",
                competitor.name,
                competitor.id,
            )


async def _monitor_competitor(competitor_id: uuid.UUID):
    """Run all monitoring checks for a single competitor."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()
        if not competitor:
            logger.warning("Competitor %s not found", competitor_id)
            return

        logger.info("Monitoring %s (%s)", competitor.name, competitor.domain)

        if competitor.track_website:
            await _crawl_website(db, competitor)

        if competitor.track_news:
            await _check_news(db, competitor)

        # Update last crawled timestamp
        competitor.last_crawled_at = datetime.now(timezone.utc)
        await db.commit()


async def _crawl_website(db: AsyncSession, competitor: Competitor):
    """Crawl competitor website pages and detect changes."""
    pages_to_crawl = [
        {"url": f"https://{competitor.domain}", "page_type": "homepage"},
        {"url": f"https://{competitor.domain}/pricing", "page_type": "pricing"},
        {"url": f"https://{competitor.domain}/product", "page_type": "product"},
    ]

    for page in pages_to_crawl:
        try:
            content = await _fetch_page_content(page["url"])
            if content is None:
                continue

            content_hash = hashlib.sha256(content.encode()).hexdigest()

            # Get the most recent snapshot for comparison
            prev_result = await db.execute(
                select(Snapshot)
                .where(
                    Snapshot.competitor_id == competitor.id,
                    Snapshot.page_type == page["page_type"],
                )
                .order_by(Snapshot.captured_at.desc())
                .limit(1)
            )
            prev_snapshot = prev_result.scalar_one_or_none()

            # Create new snapshot
            new_snapshot = Snapshot(
                competitor_id=competitor.id,
                url=page["url"],
                page_type=page["page_type"],
                content_hash=content_hash,
                markdown_content=content,
            )
            db.add(new_snapshot)
            await db.flush()

            # Detect changes if previous snapshot exists
            if prev_snapshot and prev_snapshot.content_hash != content_hash:
                await _analyze_changes(
                    db, competitor, prev_snapshot, new_snapshot
                )

        except Exception:
            logger.exception(
                "Error crawling %s for %s",
                page["url"],
                competitor.name,
            )


async def _fetch_page_content(url: str) -> str | None:
    """Fetch page content using Firecrawl or fallback to httpx."""
    if settings.firecrawl_api_key:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.firecrawl.dev/v0/scrape",
                    json={"url": url, "pageOptions": {"onlyMainContent": True}},
                    headers={"Authorization": f"Bearer {settings.firecrawl_api_key}"},
                    timeout=30.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("data", {}).get("markdown", "")
        except Exception:
            logger.warning("Firecrawl failed for %s, falling back to httpx", url)

    # Fallback: simple HTTP fetch
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url, timeout=15.0)
            if resp.status_code == 200:
                return resp.text
    except Exception:
        logger.warning("Failed to fetch %s", url)

    return None


async def _analyze_changes(
    db: AsyncSession,
    competitor: Competitor,
    old_snapshot: Snapshot,
    new_snapshot: Snapshot,
):
    """Use Claude to analyze what changed between two snapshots."""
    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        prompt = (
            f"Compare these two versions of {competitor.name}'s {new_snapshot.page_type} page "
            f"and identify the key changes.\n\n"
            f"--- OLD VERSION ---\n{(old_snapshot.markdown_content or '')[:3000]}\n\n"
            f"--- NEW VERSION ---\n{(new_snapshot.markdown_content or '')[:3000]}\n\n"
            "For each significant change found, provide:\n"
            "1. change_type: one of [pricing, messaging, feature, design, content]\n"
            "2. severity: one of [low, medium, high, critical]\n"
            "3. title: brief title (max 100 chars)\n"
            "4. summary: 1-2 sentence description\n"
            "5. significance_score: 0.0 to 1.0\n\n"
            "Respond as JSON array. If no significant changes, return []."
        )

        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        import json

        response_text = message.content[0].text
        # Extract JSON from response
        start = response_text.find("[")
        end = response_text.rfind("]") + 1
        if start >= 0 and end > start:
            changes_data = json.loads(response_text[start:end])
        else:
            changes_data = []

        for ch_data in changes_data:
            change = Change(
                competitor_id=competitor.id,
                snapshot_before_id=old_snapshot.id,
                snapshot_after_id=new_snapshot.id,
                change_type=ch_data.get("change_type", "content"),
                severity=ch_data.get("severity", "medium"),
                significance_score=ch_data.get("significance_score", 0.5),
                title=ch_data.get("title", "Untitled change"),
                summary=ch_data.get("summary"),
                page_url=new_snapshot.url,
            )
            db.add(change)

            # Generate an insight for high/critical changes
            if ch_data.get("severity") in ("high", "critical"):
                insight = Insight(
                    competitor_id=competitor.id,
                    category=_map_change_to_insight_category(
                        ch_data.get("change_type", "content")
                    ),
                    severity=ch_data.get("severity", "high"),
                    confidence=ch_data.get("significance_score", 0.8),
                    title=f"Important change: {ch_data.get('title', '')}",
                    summary=ch_data.get("summary", ""),
                    recommended_action=f"Review the {new_snapshot.page_type} page changes at {new_snapshot.url}",
                    source_refs={"change_type": ch_data.get("change_type")},
                )
                db.add(insight)

        await db.flush()
        logger.info(
            "Detected %d changes for %s (%s page)",
            len(changes_data),
            competitor.name,
            new_snapshot.page_type,
        )

    except Exception:
        logger.exception(
            "Error analyzing changes for %s", competitor.name
        )


async def _check_news(db: AsyncSession, competitor: Competitor):
    """Check for recent news about a competitor using web search."""
    try:
        async with httpx.AsyncClient() as client:
            # Use a news API or search endpoint
            resp = await client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": f'"{competitor.name}" OR "{competitor.domain}"',
                    "sortBy": "publishedAt",
                    "pageSize": 10,
                    "language": "en",
                },
                headers={"X-Api-Key": settings.firecrawl_api_key},  # placeholder
                timeout=15.0,
            )
            if resp.status_code != 200:
                return

            articles = resp.json().get("articles", [])
            for article in articles:
                # Check for duplicates by URL
                existing = await db.execute(
                    select(NewsItem).where(
                        NewsItem.competitor_id == competitor.id,
                        NewsItem.url == article.get("url"),
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                news = NewsItem(
                    competitor_id=competitor.id,
                    title=article.get("title", ""),
                    url=article.get("url", ""),
                    source=article.get("source", {}).get("name"),
                    author=article.get("author"),
                    summary=article.get("description"),
                    content=article.get("content"),
                    image_url=article.get("urlToImage"),
                    published_at=article.get("publishedAt"),
                )
                db.add(news)

            await db.flush()

    except Exception:
        logger.exception("Error checking news for %s", competitor.name)


def _map_change_to_insight_category(change_type: str) -> str:
    """Map a change type to an insight category."""
    mapping = {
        "pricing": "pricing",
        "messaging": "marketing",
        "feature": "product",
        "design": "marketing",
        "content": "strategy",
    }
    return mapping.get(change_type, "strategy")
