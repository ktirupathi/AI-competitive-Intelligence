"""Scheduled job posting monitoring tasks."""

import asyncio
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
from ..models.competitor import Competitor
from ..models.job_posting import JobPosting

logger = logging.getLogger(__name__)
settings = get_settings()


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery.task(name="apps.api.tasks.job_monitoring.run_job_monitoring_cycle")
def run_job_monitoring_cycle():
    """Scrape careers pages for all competitors with job tracking enabled."""
    logger.info("Starting job monitoring cycle")
    _run_async(_job_monitoring_cycle())
    logger.info("Job monitoring cycle complete")


@celery.task(name="apps.api.tasks.job_monitoring.monitor_jobs_for_competitor")
def monitor_jobs_for_competitor(competitor_id: str):
    """Monitor job postings for a single competitor on demand."""
    _run_async(_monitor_jobs(uuid.UUID(competitor_id)))


async def _job_monitoring_cycle():
    """Iterate competitors and scrape their careers pages."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Competitor).where(
                Competitor.user_id.isnot(None),
                Competitor.track_jobs.is_(True),
            )
        )
        competitors = list(result.scalars().all())

    logger.info("Found %d competitors for job monitoring", len(competitors))

    for comp in competitors:
        try:
            await _monitor_jobs(comp.id)
        except Exception:
            logger.exception("Error monitoring jobs for %s (%s)", comp.name, comp.id)


async def _monitor_jobs(competitor_id: uuid.UUID):
    """Scrape careers page and store new job postings for a competitor."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()
        if not competitor:
            logger.warning("Competitor %s not found", competitor_id)
            return

        if not competitor.track_jobs:
            return

        logger.info("Monitoring jobs for %s (%s)", competitor.name, competitor.domain)

        careers_url = (competitor.social_links or {}).get("careers_url")
        base_url = f"https://{competitor.domain}"

        urls_to_try = []
        if careers_url:
            urls_to_try.append(careers_url)
        urls_to_try.extend([
            f"{base_url}/careers",
            f"{base_url}/jobs",
            f"{base_url}/careers/open-positions",
        ])

        content = ""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            if settings.firecrawl_api_key:
                for url in urls_to_try:
                    try:
                        resp = await client.post(
                            "https://api.firecrawl.dev/v1/scrape",
                            json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
                            headers={"Authorization": f"Bearer {settings.firecrawl_api_key}"},
                            timeout=40.0,
                        )
                        if resp.status_code == 200:
                            md = resp.json().get("data", {}).get("markdown", "")
                            if md and len(md) > 200:
                                content = md
                                break
                    except Exception:
                        continue

            # Fallback: httpx
            if not content:
                for url in urls_to_try:
                    try:
                        resp = await client.get(url, timeout=15.0)
                        if resp.status_code == 200 and len(resp.text) > 200:
                            content = resp.text
                            break
                    except Exception:
                        continue

        if not content:
            logger.info("No careers page content found for %s", competitor.name)
            return

        # Use Claude to extract job postings
        try:
            anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            response = await anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                temperature=0.1,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Extract job postings from this careers page for {competitor.name}.\n\n"
                        f"Content:\n{content[:5000]}\n\n"
                        "Return ONLY a JSON array of objects with: title, department, location, seniority_level.\n"
                        "If no jobs found, return []."
                    ),
                }],
            )
            import json
            raw = response.content[0].text.strip()
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                jobs_data = json.loads(raw[start:end])
            else:
                jobs_data = []
        except Exception:
            logger.exception("LLM job extraction failed for %s", competitor.name)
            jobs_data = []

        # Store new postings (deduplicate by title)
        existing_result = await db.execute(
            select(JobPosting.title).where(
                JobPosting.competitor_id == competitor.id,
                JobPosting.is_active.is_(True),
            )
        )
        existing_titles = {row[0].lower() for row in existing_result.all()}

        new_count = 0
        for job in jobs_data:
            title = job.get("title", "").strip()
            if not title or title.lower() in existing_titles:
                continue

            posting = JobPosting(
                competitor_id=competitor.id,
                title=title,
                url=careers_url or f"{base_url}/careers",
                department=job.get("department"),
                location=job.get("location"),
                seniority_level=job.get("seniority_level"),
            )
            db.add(posting)
            new_count += 1

        await db.commit()
        logger.info("Found %d new jobs for %s", new_count, competitor.name)
