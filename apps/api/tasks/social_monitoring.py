"""Scheduled social media monitoring tasks."""

import asyncio
import json
import logging
import uuid

import anthropic
import httpx
from sqlalchemy import select

from ..celery_app import celery
from ..config import get_settings
from ..database import async_session_factory
from ..models.competitor import Competitor
from ..models.social_post import SocialPost

logger = logging.getLogger(__name__)
settings = get_settings()


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery.task(name="apps.api.tasks.social_monitoring.run_social_monitoring_cycle")
def run_social_monitoring_cycle():
    """Monitor social media for all competitors with social tracking enabled."""
    logger.info("Starting social monitoring cycle")
    _run_async(_social_monitoring_cycle())
    logger.info("Social monitoring cycle complete")


@celery.task(name="apps.api.tasks.social_monitoring.monitor_social_for_competitor")
def monitor_social_for_competitor(competitor_id: str):
    """Monitor social media for a single competitor on demand."""
    _run_async(_monitor_social(uuid.UUID(competitor_id)))


async def _social_monitoring_cycle():
    """Iterate competitors and monitor their social presence."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Competitor).where(
                Competitor.user_id.isnot(None),
                Competitor.track_social.is_(True),
            )
        )
        competitors = list(result.scalars().all())

    logger.info("Found %d competitors for social monitoring", len(competitors))

    for comp in competitors:
        try:
            await _monitor_social(comp.id)
        except Exception:
            logger.exception(
                "Error monitoring social for %s (%s)", comp.name, comp.id
            )


async def _monitor_social(competitor_id: uuid.UUID):
    """Monitor LinkedIn and Twitter for a single competitor."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()
        if not competitor:
            logger.warning("Competitor %s not found", competitor_id)
            return

        if not competitor.track_social:
            return

        social_links = competitor.social_links or {}
        linkedin_url = social_links.get("linkedin_url")
        twitter_handle = social_links.get("twitter_handle")

        posts_data: list[dict] = []

        # LinkedIn monitoring via web search
        if linkedin_url:
            try:
                posts = await _search_social_posts(
                    competitor.name, "linkedin", linkedin_url
                )
                posts_data.extend(posts)
            except Exception:
                logger.exception(
                    "LinkedIn monitoring failed for %s", competitor.name
                )

        # Twitter monitoring via web search
        if twitter_handle:
            handle = twitter_handle.lstrip("@")
            try:
                posts = await _search_social_posts(
                    competitor.name, "twitter", f"https://x.com/{handle}"
                )
                posts_data.extend(posts)
            except Exception:
                logger.exception(
                    "Twitter monitoring failed for %s", competitor.name
                )

        # Reddit mentions
        try:
            reddit_posts = await _search_reddit_mentions(competitor.name)
            posts_data.extend(reddit_posts)
        except Exception:
            logger.exception("Reddit monitoring failed for %s", competitor.name)

        if not posts_data:
            logger.info("No social posts found for %s", competitor.name)
            return

        # Classify and store posts
        existing_urls = set()
        existing_result = await db.execute(
            select(SocialPost.url).where(
                SocialPost.competitor_id == competitor.id,
                SocialPost.url.isnot(None),
            )
        )
        existing_urls = {row[0] for row in existing_result.all() if row[0]}

        new_count = 0
        for post in posts_data:
            url = post.get("url", "")
            if url and url in existing_urls:
                continue

            # Classify with LLM
            classification = await _classify_post(competitor.name, post)

            social_post = SocialPost(
                competitor_id=competitor.id,
                platform=post.get("platform", "unknown"),
                url=url or None,
                content=post.get("content", "")[:2000],
                likes=post.get("likes", 0),
                shares=post.get("shares", 0),
                comments_count=post.get("comments", 0),
                sentiment=classification.get("sentiment"),
                topics=classification.get("topics", []),
            )
            db.add(social_post)
            new_count += 1

        await db.commit()
        logger.info("Stored %d new social posts for %s", new_count, competitor.name)


async def _search_social_posts(
    company_name: str, platform: str, profile_url: str
) -> list[dict]:
    """Search for recent social posts via Firecrawl or web search fallback."""
    posts: list[dict] = []

    # Try Firecrawl first
    if settings.firecrawl_api_key:
        try:
            async with httpx.AsyncClient() as client:
                activity_url = profile_url.rstrip("/") + (
                    "/posts/" if platform == "linkedin" else ""
                )
                resp = await client.post(
                    "https://api.firecrawl.dev/v1/scrape",
                    json={
                        "url": activity_url,
                        "formats": ["markdown"],
                        "onlyMainContent": True,
                    },
                    headers={"Authorization": f"Bearer {settings.firecrawl_api_key}"},
                    timeout=40.0,
                )
                if resp.status_code == 200:
                    content = resp.json().get("data", {}).get("markdown", "")
                    if content and len(content) > 100:
                        # Parse with LLM
                        extracted = await _extract_posts_with_llm(
                            company_name, platform, content
                        )
                        posts.extend(extracted)
        except Exception as exc:
            logger.warning("Firecrawl social scrape failed: %s", exc)

    return posts


async def _search_reddit_mentions(company_name: str) -> list[dict]:
    """Search Reddit for mentions of the company via web search."""
    # This requires a search API key; skip if not configured
    if not settings.firecrawl_api_key:
        return []

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.firecrawl.dev/v1/scrape",
                json={
                    "url": f"https://www.reddit.com/search/?q={company_name}&sort=new",
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                },
                headers={"Authorization": f"Bearer {settings.firecrawl_api_key}"},
                timeout=40.0,
            )
            if resp.status_code == 200:
                content = resp.json().get("data", {}).get("markdown", "")
                if content:
                    return await _extract_posts_with_llm(
                        company_name, "reddit", content
                    )
    except Exception as exc:
        logger.warning("Reddit search failed for %s: %s", company_name, exc)

    return []


async def _extract_posts_with_llm(
    company_name: str, platform: str, content: str
) -> list[dict]:
    """Extract structured post data from scraped social media content."""
    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            temperature=0.1,
            messages=[{
                "role": "user",
                "content": (
                    f"Extract social media posts about {company_name} from this {platform} content.\n\n"
                    f"Content:\n{content[:5000]}\n\n"
                    "Return ONLY a JSON array of post objects with:\n"
                    '  platform, content (text), url, likes (int), comments (int), shares (int)\n'
                    "If no relevant posts found, return []."
                ),
            }],
        )
        raw = response.content[0].text.strip()
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            posts = json.loads(raw[start:end])
            for p in posts:
                p["platform"] = platform
            return posts
    except Exception:
        logger.exception("LLM post extraction failed for %s", company_name)

    return []


async def _classify_post(company_name: str, post: dict) -> dict:
    """Use Claude to classify a social media post."""
    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            temperature=0.1,
            messages=[{
                "role": "user",
                "content": (
                    f"Classify this {post.get('platform', 'social')} post related to {company_name}.\n\n"
                    f"Content: {post.get('content', '')[:1000]}\n\n"
                    "Return ONLY JSON:\n"
                    '{"sentiment": "positive|negative|neutral", "topics": ["topic1", "topic2"]}'
                ),
            }],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            raw = "\n".join(lines)
        return json.loads(raw)
    except Exception:
        return {"sentiment": "neutral", "topics": []}
