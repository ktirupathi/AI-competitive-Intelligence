"""
Scout AI - Job Posting Agent

Monitors competitor careers pages for job postings, identifies hiring
patterns and strategic signals using Claude analysis.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

import anthropic
import httpx

from agents.config import settings
from agents.prompts import JOB_ANALYSIS_SYSTEM, JOB_ANALYSIS_USER
from agents.state import JobPosting, PipelineState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Careers page scraping
# ---------------------------------------------------------------------------

# Common careers page URL patterns to try
CAREERS_PATHS = [
    "/careers",
    "/jobs",
    "/careers/open-positions",
    "/about/careers",
    "/company/careers",
    "/join",
    "/team",
    "/work-with-us",
]


async def _scrape_careers_page(
    base_url: str, careers_url: str | None, client: httpx.AsyncClient
) -> str:
    """Attempt to scrape the careers page. Try known paths if no explicit URL."""
    urls_to_try: List[str] = []

    if careers_url:
        urls_to_try.append(careers_url)

    base = base_url.rstrip("/")
    if not base.startswith("http"):
        base = f"https://{base}"
    urls_to_try.extend([f"{base}{path}" for path in CAREERS_PATHS])

    if settings.firecrawl.api_key:
        headers = {
            "Authorization": f"Bearer {settings.firecrawl.api_key}",
            "Content-Type": "application/json",
        }
        for url in urls_to_try:
            try:
                resp = await client.post(
                    f"{settings.firecrawl.base_url}/scrape",
                    json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
                    headers=headers,
                    timeout=settings.firecrawl.timeout + 10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("data", {}).get("markdown", "")
                    if content and len(content) > 100:
                        return content
            except Exception:
                continue

    # Fallback: plain httpx
    for url in urls_to_try:
        try:
            resp = await client.get(url, timeout=20, follow_redirects=True)
            if resp.status_code == 200 and len(resp.text) > 200:
                return resp.text
        except Exception:
            continue

    return ""


def _extract_job_blocks(content: str) -> List[Dict[str, str]]:
    """
    Heuristic extraction of individual job postings from a careers page.
    Returns a list of dicts with 'title', 'department', 'location', 'description'.
    """
    jobs: List[Dict[str, str]] = []

    # Try to find markdown-style job blocks (## Title pattern)
    md_pattern = re.compile(
        r"(?:^|\n)#{1,3}\s+(.+?)(?:\n(?:Department|Team|Group):\s*(.+?))?(?:\n(?:Location):\s*(.+?))?(?:\n([\s\S]*?))?(?=\n#{1,3}\s|\Z)",
        re.IGNORECASE,
    )
    for match in md_pattern.finditer(content):
        title = match.group(1).strip()
        # Filter out non-job headings
        if any(kw in title.lower() for kw in ["career", "join", "open position", "perks", "benefit", "our culture"]):
            continue
        jobs.append({
            "title": title,
            "department": (match.group(2) or "").strip(),
            "location": (match.group(3) or "").strip(),
            "description": (match.group(4) or "").strip()[:2000],
        })

    # If markdown parsing found nothing, try line-based heuristic
    if not jobs:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            line = line.strip()
            # Look for lines that look like job titles
            if (
                10 < len(line) < 120
                and any(
                    kw in line.lower()
                    for kw in [
                        "engineer",
                        "manager",
                        "designer",
                        "analyst",
                        "director",
                        "developer",
                        "architect",
                        "scientist",
                        "lead",
                        "head of",
                        "vp ",
                        "specialist",
                        "coordinator",
                    ]
                )
            ):
                # Gather a few subsequent lines as context
                context = "\n".join(lines[i : i + 5])
                jobs.append({
                    "title": line.strip("*#- "),
                    "department": "",
                    "location": "",
                    "description": context[:2000],
                })

    return jobs[:50]  # Cap at 50 postings per competitor


# ---------------------------------------------------------------------------
# Claude analysis
# ---------------------------------------------------------------------------


async def _analyse_job(
    competitor_name: str, title: str, department: str, location: str, description: str
) -> Dict[str, Any]:
    """Use Claude Haiku to extract strategic signals from a job posting."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic.api_key)

    user_msg = JOB_ANALYSIS_USER.format(
        competitor_name=competitor_name,
        title=title,
        department=department or "Not specified",
        location=location or "Not specified",
        description=description or "No description available",
    )

    try:
        response = await client.messages.create(
            model=settings.anthropic.classification_model,
            max_tokens=settings.anthropic.max_tokens_classification,
            temperature=settings.anthropic.temperature_classification,
            system=JOB_ANALYSIS_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        return json.loads(response.content[0].text.strip())
    except (json.JSONDecodeError, IndexError, anthropic.APIError) as exc:
        logger.error("Job analysis failed for '%s': %s", title, exc)
        return {
            "seniority": "mid",
            "department": "other",
            "strategic_signal": "Analysis unavailable",
            "technologies_mentioned": [],
            "urgency_indicators": "medium",
        }


# ---------------------------------------------------------------------------
# Core agent function
# ---------------------------------------------------------------------------


async def job_agent(state: PipelineState) -> PipelineState:
    """
    LangGraph node: scrape careers pages, extract and analyse job postings.

    Reads:
        state["competitors"]
    Writes:
        state["job_postings"]
    """
    competitors = state.get("competitors", [])
    errors: List[Dict[str, Any]] = list(state.get("errors", []))
    all_jobs: List[JobPosting] = []

    async with httpx.AsyncClient() as http_client:
        sem = asyncio.Semaphore(settings.pipeline.max_concurrent_competitors)

        async def _process_competitor(comp: Dict[str, Any]) -> None:
            async with sem:
                name = comp["name"]
                domain = comp["domain"]
                careers_url = comp.get("careers_url")

                try:
                    content = await _scrape_careers_page(domain, careers_url, http_client)
                    if not content:
                        logger.warning("No careers page content found for %s", name)
                        return

                    raw_jobs = _extract_job_blocks(content)
                    logger.info("Extracted %d job blocks from %s", len(raw_jobs), name)

                    for raw in raw_jobs:
                        analysis = await _analyse_job(
                            competitor_name=name,
                            title=raw["title"],
                            department=raw.get("department", ""),
                            location=raw.get("location", ""),
                            description=raw.get("description", ""),
                        )

                        posting: JobPosting = {
                            "competitor_name": name,
                            "title": raw["title"],
                            "department": analysis.get("department", "other"),
                            "seniority": analysis.get("seniority", "mid"),
                            "location": raw.get("location", "Not specified"),
                            "url": careers_url or f"https://{domain}/careers",
                            "posted_at": None,
                            "strategic_signal": analysis.get("strategic_signal", ""),
                        }
                        all_jobs.append(posting)

                except Exception as exc:
                    logger.error("Job agent failed for %s: %s", name, exc)
                    errors.append({
                        "agent": "job",
                        "competitor": name,
                        "error": str(exc),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

        await asyncio.gather(
            *[_process_competitor(comp) for comp in competitors]
        )

    logger.info("Job agent complete: %d postings collected", len(all_jobs))

    return {
        "job_postings": all_jobs,
        "errors": errors,
    }
