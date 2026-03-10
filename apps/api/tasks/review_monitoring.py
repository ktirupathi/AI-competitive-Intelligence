"""Scheduled review scraping tasks."""

import asyncio
import json
import logging
import uuid

import anthropic
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..celery_app import celery
from ..config import get_settings
from ..database import async_session_factory
from ..models.competitor import Competitor
from ..models.review import Review

logger = logging.getLogger(__name__)
settings = get_settings()


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery.task(name="apps.api.tasks.review_monitoring.run_review_monitoring_cycle")
def run_review_monitoring_cycle():
    """Scrape G2/Capterra reviews for all competitors with review tracking."""
    logger.info("Starting review monitoring cycle")
    _run_async(_review_monitoring_cycle())
    logger.info("Review monitoring cycle complete")


@celery.task(name="apps.api.tasks.review_monitoring.scrape_reviews_for_competitor")
def scrape_reviews_for_competitor(competitor_id: str):
    """Scrape reviews for a single competitor on demand."""
    _run_async(_scrape_reviews(uuid.UUID(competitor_id)))


async def _review_monitoring_cycle():
    """Iterate competitors and scrape reviews."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Competitor).where(
                Competitor.user_id.isnot(None),
                Competitor.track_reviews.is_(True),
            )
        )
        competitors = list(result.scalars().all())

    logger.info("Found %d competitors for review monitoring", len(competitors))

    for comp in competitors:
        try:
            await _scrape_reviews(comp.id)
        except Exception:
            logger.exception("Error scraping reviews for %s (%s)", comp.name, comp.id)


async def _scrape_reviews(competitor_id: uuid.UUID):
    """Scrape G2 and Capterra for a single competitor's reviews."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()
        if not competitor:
            logger.warning("Competitor %s not found", competitor_id)
            return

        if not competitor.track_reviews:
            return

        social_links = competitor.social_links or {}
        g2_slug = social_links.get("g2_slug")
        capterra_slug = social_links.get("capterra_slug")

        platforms: list[tuple[str, str]] = []
        if g2_slug:
            platforms.append(("g2", f"https://www.g2.com/products/{g2_slug}/reviews"))
        if capterra_slug:
            platforms.append(("capterra", f"https://www.capterra.com/p/{capterra_slug}/reviews/"))

        if not platforms:
            # Try searching for the company name on G2
            platforms.append(("g2", f"https://www.g2.com/search?query={competitor.name}"))

        for platform, url in platforms:
            try:
                content = await _fetch_review_page(url)
                if not content or len(content) < 100:
                    continue

                reviews_data = await _extract_reviews_with_llm(
                    competitor.name, platform, content
                )

                # Store new reviews (simple dedup by title + platform)
                existing = await db.execute(
                    select(Review.title).where(
                        Review.competitor_id == competitor.id,
                        Review.platform == platform,
                    )
                )
                existing_titles = {(row[0] or "").lower() for row in existing.all()}

                new_count = 0
                for rev in reviews_data:
                    title = rev.get("title", "").strip()
                    if title.lower() in existing_titles:
                        continue

                    review = Review(
                        competitor_id=competitor.id,
                        platform=platform,
                        title=title or "Untitled Review",
                        rating=rev.get("rating"),
                        star_rating=int(rev.get("rating", 0)) if rev.get("rating") else None,
                        body=rev.get("text", ""),
                        pros=rev.get("pros"),
                        cons=rev.get("cons"),
                        sentiment=rev.get("sentiment", "neutral"),
                        sentiment_score=rev.get("sentiment_score"),
                    )
                    db.add(review)
                    new_count += 1

                await db.commit()
                logger.info(
                    "Stored %d new %s reviews for %s",
                    new_count, platform, competitor.name,
                )

            except Exception:
                logger.exception(
                    "Review scraping failed for %s on %s", competitor.name, platform
                )


async def _fetch_review_page(url: str) -> str:
    """Fetch a review page, preferring Firecrawl."""
    if settings.firecrawl_api_key:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.firecrawl.dev/v1/scrape",
                    json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
                    headers={"Authorization": f"Bearer {settings.firecrawl_api_key}"},
                    timeout=40.0,
                )
                if resp.status_code == 200:
                    return resp.json().get("data", {}).get("markdown", "")
        except Exception as exc:
            logger.warning("Firecrawl failed for %s: %s", url, exc)

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(
                url,
                timeout=20.0,
                headers={"User-Agent": "Mozilla/5.0 (compatible; ScoutAI/1.0)"},
            )
            if resp.status_code == 200:
                return resp.text
    except Exception as exc:
        logger.warning("httpx fetch failed for %s: %s", url, exc)

    return ""


async def _extract_reviews_with_llm(
    competitor_name: str, platform: str, content: str
) -> list[dict]:
    """Use Claude to extract structured review data from scraped content."""
    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            temperature=0.1,
            messages=[{
                "role": "user",
                "content": (
                    f"Extract customer reviews from this {platform} page for {competitor_name}.\n\n"
                    f"Content:\n{content[:5000]}\n\n"
                    "Return ONLY a JSON array of review objects with:\n"
                    "  title, rating (float 0-5), text, pros, cons,\n"
                    "  sentiment (positive|negative|mixed|neutral),\n"
                    "  sentiment_score (float -1 to 1)\n"
                    "If no reviews found, return []."
                ),
            }],
        )
        raw = response.content[0].text.strip()
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except Exception:
        logger.exception("LLM review extraction failed for %s", competitor_name)

    return []
