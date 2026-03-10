"""
Scout AI - Review Agent

Scrapes G2 and Capterra review pages for competitor products, extracts
sentiment and themes using Claude analysis.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import anthropic
import httpx

from agents.config import settings
from agents.prompts import REVIEW_ANALYSIS_SYSTEM, REVIEW_ANALYSIS_USER
from agents.state import PipelineState, Review

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Review scraping helpers
# ---------------------------------------------------------------------------


async def _scrape_page(url: str, client: httpx.AsyncClient) -> str:
    """Scrape a review page, preferring Firecrawl, falling back to httpx."""
    if settings.firecrawl.api_key:
        try:
            headers = {
                "Authorization": f"Bearer {settings.firecrawl.api_key}",
                "Content-Type": "application/json",
            }
            resp = await client.post(
                f"{settings.firecrawl.base_url}/scrape",
                json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
                headers=headers,
                timeout=settings.firecrawl.timeout + 10,
            )
            if resp.status_code == 200:
                return resp.json().get("data", {}).get("markdown", "")
        except Exception as exc:
            logger.warning("Firecrawl failed for %s: %s", url, exc)

    try:
        resp = await client.get(
            url,
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ScoutAI/1.0)"},
        )
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.warning("httpx scrape failed for %s: %s", url, exc)

    return ""


def _build_g2_url(slug: str) -> str:
    """Build a G2 reviews page URL from a product slug."""
    return f"https://www.g2.com/products/{slug}/reviews"


def _build_capterra_url(slug: str) -> str:
    """Build a Capterra reviews page URL from a product slug."""
    return f"https://www.capterra.com/p/{slug}/reviews/"


def _extract_reviews_from_content(
    content: str, platform: str
) -> List[Dict[str, Any]]:
    """
    Heuristic extraction of individual reviews from scraped markdown/HTML.
    Returns list of dicts with title, rating, text, reviewer_role, date.
    """
    reviews: List[Dict[str, Any]] = []

    if platform == "g2":
        # G2 markdown often has review blocks separated by "---" or headings
        # Look for star rating patterns and review text
        blocks = re.split(r"\n---+\n|\n#{1,3}\s+(?=\d)", content)
        for block in blocks:
            if len(block.strip()) < 50:
                continue

            rating_match = re.search(r"(\d(?:\.\d)?)\s*(?:/\s*5|out of 5|stars?|★)", block, re.IGNORECASE)
            rating = float(rating_match.group(1)) if rating_match else 0.0

            # Try to find title (often first meaningful line)
            lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
            title = ""
            for line in lines[:3]:
                clean = line.strip("*#- ")
                if 10 < len(clean) < 150 and not re.match(r"^\d", clean):
                    title = clean
                    break

            if not title and not rating:
                continue

            reviews.append({
                "title": title or "Untitled Review",
                "rating": rating,
                "text": block.strip()[:3000],
                "reviewer_role": None,
                "date": None,
            })

    elif platform == "capterra":
        blocks = re.split(r"\n---+\n|\n#{1,3}\s+", content)
        for block in blocks:
            if len(block.strip()) < 50:
                continue

            rating_match = re.search(r"(\d(?:\.\d)?)\s*(?:/\s*5|out of 5|stars?|Overall)", block, re.IGNORECASE)
            rating = float(rating_match.group(1)) if rating_match else 0.0

            lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
            title = ""
            for line in lines[:3]:
                clean = line.strip("*#- ")
                if 10 < len(clean) < 150:
                    title = clean
                    break

            if not title and not rating:
                continue

            # Try to find role/industry
            role_match = re.search(
                r"(?:Industry|Role|Title|Position):\s*(.+)", block, re.IGNORECASE
            )
            reviewer_role = role_match.group(1).strip() if role_match else None

            reviews.append({
                "title": title or "Untitled Review",
                "rating": rating,
                "text": block.strip()[:3000],
                "reviewer_role": reviewer_role,
                "date": None,
            })

    return reviews[:30]  # Cap per platform per competitor


# ---------------------------------------------------------------------------
# Claude analysis
# ---------------------------------------------------------------------------


async def _analyse_review(
    competitor_name: str,
    platform: str,
    rating: float,
    title: str,
    review_text: str,
) -> Dict[str, Any]:
    """Use Claude Haiku to extract sentiment and themes from a review."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic.api_key)

    user_msg = REVIEW_ANALYSIS_USER.format(
        competitor_name=competitor_name,
        platform=platform,
        rating=rating,
        title=title,
        review_text=review_text[:2000],
    )

    try:
        response = await client.messages.create(
            model=settings.anthropic.classification_model,
            max_tokens=settings.anthropic.max_tokens_classification,
            temperature=settings.anthropic.temperature_classification,
            system=REVIEW_ANALYSIS_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        return json.loads(response.content[0].text.strip())
    except (json.JSONDecodeError, IndexError, anthropic.APIError) as exc:
        logger.error("Review analysis failed for '%s': %s", title, exc)
        return {
            "sentiment": "neutral",
            "pros_summary": "",
            "cons_summary": "",
            "key_themes": [],
            "competitive_relevance": "",
        }


# ---------------------------------------------------------------------------
# Core agent function
# ---------------------------------------------------------------------------


async def review_agent(state: PipelineState) -> PipelineState:
    """
    LangGraph node: scrape G2/Capterra reviews, analyse sentiment & themes.

    Reads:
        state["competitors"]
    Writes:
        state["reviews"]
    """
    competitors = state.get("competitors", [])
    errors: List[Dict[str, Any]] = list(state.get("errors", []))
    all_reviews: List[Review] = []

    async with httpx.AsyncClient() as http_client:
        sem = asyncio.Semaphore(settings.pipeline.max_concurrent_competitors)

        async def _process_competitor(comp: Dict[str, Any]) -> None:
            async with sem:
                name = comp["name"]
                g2_slug = comp.get("g2_slug")
                capterra_slug = comp.get("capterra_slug")

                platforms: List[tuple[str, str]] = []
                if g2_slug:
                    platforms.append(("g2", _build_g2_url(g2_slug)))
                if capterra_slug:
                    platforms.append(("capterra", _build_capterra_url(capterra_slug)))

                if not platforms:
                    logger.info("No review platform slugs configured for %s, skipping", name)
                    return

                for platform, url in platforms:
                    try:
                        content = await _scrape_page(url, http_client)
                        if not content:
                            logger.warning("No review content from %s for %s", platform, name)
                            continue

                        raw_reviews = _extract_reviews_from_content(content, platform)
                        logger.info(
                            "Extracted %d reviews from %s for %s",
                            len(raw_reviews),
                            platform,
                            name,
                        )

                        for raw in raw_reviews:
                            analysis = await _analyse_review(
                                competitor_name=name,
                                platform=platform,
                                rating=raw["rating"],
                                title=raw["title"],
                                review_text=raw["text"],
                            )

                            review: Review = {
                                "competitor_name": name,
                                "platform": platform,
                                "rating": raw["rating"],
                                "title": raw["title"],
                                "pros": analysis.get("pros_summary", ""),
                                "cons": analysis.get("cons_summary", ""),
                                "reviewer_role": raw.get("reviewer_role"),
                                "date": raw.get("date"),
                                "sentiment": analysis.get("sentiment", "neutral"),
                                "key_themes": analysis.get("key_themes", []),
                            }
                            all_reviews.append(review)

                    except Exception as exc:
                        logger.error(
                            "Review scraping failed for %s on %s: %s",
                            name,
                            platform,
                            exc,
                        )
                        errors.append({
                            "agent": "review",
                            "competitor": name,
                            "platform": platform,
                            "error": str(exc),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })

        await asyncio.gather(
            *[_process_competitor(comp) for comp in competitors]
        )

    logger.info("Review agent complete: %d reviews collected", len(all_reviews))

    return {
        "reviews": all_reviews,
        "errors": errors,
    }
