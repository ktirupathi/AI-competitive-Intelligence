"""
Scout AI - Social Media Agent

Monitors LinkedIn and Twitter/X posts for competitor accounts, classifies
post types, and tracks engagement metrics.
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
from agents.prompts import SOCIAL_CLASSIFICATION_SYSTEM, SOCIAL_CLASSIFICATION_USER
from agents.state import PipelineState, SocialPost

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Social media scraping helpers
# ---------------------------------------------------------------------------


async def _scrape_linkedin_posts(
    linkedin_url: str, client: httpx.AsyncClient
) -> List[Dict[str, Any]]:
    """
    Scrape recent posts from a LinkedIn company page.

    Uses Firecrawl if available (best results), otherwise falls back to
    httpx with limited extraction capability.
    """
    posts: List[Dict[str, Any]] = []
    # Ensure we target the posts/activity feed
    activity_url = linkedin_url.rstrip("/") + "/posts/"

    if settings.firecrawl.api_key:
        try:
            headers = {
                "Authorization": f"Bearer {settings.firecrawl.api_key}",
                "Content-Type": "application/json",
            }
            resp = await client.post(
                f"{settings.firecrawl.base_url}/scrape",
                json={
                    "url": activity_url,
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                },
                headers=headers,
                timeout=settings.firecrawl.timeout + 10,
            )
            if resp.status_code == 200:
                content = resp.json().get("data", {}).get("markdown", "")
                posts = _parse_linkedin_markdown(content, linkedin_url)
        except Exception as exc:
            logger.warning("Firecrawl LinkedIn scrape failed: %s", exc)

    # Fallback: use web search to find recent LinkedIn posts
    if not posts and settings.web_search.api_key:
        try:
            company_name = linkedin_url.rstrip("/").split("/")[-1]
            search_resp = await client.post(
                f"{settings.web_search.serper_base_url}/search",
                json={
                    "q": f"site:linkedin.com/posts {company_name}",
                    "num": 10,
                },
                headers={
                    "X-API-KEY": settings.web_search.api_key,
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            if search_resp.status_code == 200:
                for item in search_resp.json().get("organic", []):
                    posts.append({
                        "platform": "linkedin",
                        "author": company_name,
                        "content": item.get("snippet", ""),
                        "url": item.get("link", ""),
                        "posted_at": item.get("date"),
                        "likes": 0,
                        "comments": 0,
                        "shares": 0,
                    })
        except Exception as exc:
            logger.warning("LinkedIn search fallback failed: %s", exc)

    return posts


def _parse_linkedin_markdown(content: str, base_url: str) -> List[Dict[str, Any]]:
    """Parse LinkedIn post blocks from Firecrawl markdown output."""
    posts: List[Dict[str, Any]] = []
    company = base_url.rstrip("/").split("/")[-1]

    # Split on likely post boundaries
    blocks = re.split(r"\n---+\n|\n#{1,3}\s+", content)
    for block in blocks:
        block = block.strip()
        if len(block) < 30:
            continue

        # Try to extract engagement numbers
        likes = _extract_metric(block, r"(\d[\d,]*)\s*(?:like|reaction)", 0)
        comments = _extract_metric(block, r"(\d[\d,]*)\s*comment", 0)
        shares = _extract_metric(block, r"(\d[\d,]*)\s*(?:repost|share)", 0)

        posts.append({
            "platform": "linkedin",
            "author": company,
            "content": block[:2000],
            "url": None,
            "posted_at": None,
            "likes": likes,
            "comments": comments,
            "shares": shares,
        })

    return posts[:20]


async def _scrape_twitter_posts(
    twitter_handle: str, client: httpx.AsyncClient
) -> List[Dict[str, Any]]:
    """
    Gather recent Twitter/X posts for a competitor handle.

    Primary method: web search for recent tweets.
    Firecrawl is attempted first if configured.
    """
    posts: List[Dict[str, Any]] = []
    handle = twitter_handle.lstrip("@")
    profile_url = f"https://x.com/{handle}"

    # Attempt Firecrawl scrape of profile
    if settings.firecrawl.api_key:
        try:
            headers = {
                "Authorization": f"Bearer {settings.firecrawl.api_key}",
                "Content-Type": "application/json",
            }
            resp = await client.post(
                f"{settings.firecrawl.base_url}/scrape",
                json={
                    "url": profile_url,
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                },
                headers=headers,
                timeout=settings.firecrawl.timeout + 10,
            )
            if resp.status_code == 200:
                content = resp.json().get("data", {}).get("markdown", "")
                posts = _parse_twitter_markdown(content, handle)
        except Exception as exc:
            logger.warning("Firecrawl Twitter scrape failed for @%s: %s", handle, exc)

    # Fallback: search for recent tweets
    if not posts and settings.web_search.api_key:
        try:
            search_resp = await client.post(
                f"{settings.web_search.serper_base_url}/search",
                json={
                    "q": f"site:twitter.com/{handle} OR site:x.com/{handle}",
                    "num": 10,
                },
                headers={
                    "X-API-KEY": settings.web_search.api_key,
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            if search_resp.status_code == 200:
                for item in search_resp.json().get("organic", []):
                    posts.append({
                        "platform": "twitter",
                        "author": f"@{handle}",
                        "content": item.get("snippet", ""),
                        "url": item.get("link", ""),
                        "posted_at": item.get("date"),
                        "likes": 0,
                        "comments": 0,
                        "shares": 0,
                    })
        except Exception as exc:
            logger.warning("Twitter search fallback failed for @%s: %s", handle, exc)

    return posts


def _parse_twitter_markdown(content: str, handle: str) -> List[Dict[str, Any]]:
    """Parse tweet blocks from Firecrawl markdown output."""
    posts: List[Dict[str, Any]] = []

    blocks = re.split(r"\n---+\n", content)
    for block in blocks:
        block = block.strip()
        if len(block) < 20:
            continue

        likes = _extract_metric(block, r"(\d[\d,]*)\s*(?:like|heart)", 0)
        comments = _extract_metric(block, r"(\d[\d,]*)\s*(?:repl|comment)", 0)
        shares = _extract_metric(block, r"(\d[\d,]*)\s*(?:retweet|repost|share)", 0)

        posts.append({
            "platform": "twitter",
            "author": f"@{handle}",
            "content": block[:2000],
            "url": None,
            "posted_at": None,
            "likes": likes,
            "comments": comments,
            "shares": shares,
        })

    return posts[:20]


def _extract_metric(text: str, pattern: str, default: int) -> int:
    """Extract a numeric engagement metric from text."""
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1).replace(",", ""))
        except ValueError:
            pass
    return default


# ---------------------------------------------------------------------------
# Claude classification
# ---------------------------------------------------------------------------


async def _classify_post(
    competitor_name: str,
    platform: str,
    author: str,
    content: str,
    likes: int,
    comments: int,
    shares: int,
) -> Dict[str, Any]:
    """Use Claude Haiku to classify a social media post."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic.api_key)

    user_msg = SOCIAL_CLASSIFICATION_USER.format(
        competitor_name=competitor_name,
        platform=platform,
        author=author,
        content=content[:1500],
        likes=likes,
        comments=comments,
        shares=shares,
    )

    try:
        response = await client.messages.create(
            model=settings.anthropic.classification_model,
            max_tokens=settings.anthropic.max_tokens_classification,
            temperature=settings.anthropic.temperature_classification,
            system=SOCIAL_CLASSIFICATION_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        return json.loads(response.content[0].text.strip())
    except (json.JSONDecodeError, IndexError, anthropic.APIError) as exc:
        logger.error("Social classification failed: %s", exc)
        return {
            "post_type": "other",
            "summary": content[:100],
            "engagement_score": 0.0,
            "strategic_relevance": "low",
            "key_topics": [],
        }


# ---------------------------------------------------------------------------
# Core agent function
# ---------------------------------------------------------------------------


async def social_agent(state: PipelineState) -> PipelineState:
    """
    LangGraph node: monitor LinkedIn & Twitter, classify posts.

    Reads:
        state["competitors"]
    Writes:
        state["social_posts"]
    """
    competitors = state.get("competitors", [])
    errors: List[Dict[str, Any]] = list(state.get("errors", []))
    all_posts: List[SocialPost] = []

    async with httpx.AsyncClient() as http_client:
        sem = asyncio.Semaphore(settings.pipeline.max_concurrent_competitors)

        async def _process_competitor(comp: Dict[str, Any]) -> None:
            async with sem:
                name = comp["name"]
                raw_posts: List[Dict[str, Any]] = []

                # LinkedIn
                if comp.get("linkedin_url"):
                    try:
                        li_posts = await _scrape_linkedin_posts(
                            comp["linkedin_url"], http_client
                        )
                        raw_posts.extend(li_posts)
                    except Exception as exc:
                        logger.error("LinkedIn scraping failed for %s: %s", name, exc)
                        errors.append({
                            "agent": "social",
                            "competitor": name,
                            "platform": "linkedin",
                            "error": str(exc),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })

                # Twitter/X
                if comp.get("twitter_handle"):
                    try:
                        tw_posts = await _scrape_twitter_posts(
                            comp["twitter_handle"], http_client
                        )
                        raw_posts.extend(tw_posts)
                    except Exception as exc:
                        logger.error("Twitter scraping failed for %s: %s", name, exc)
                        errors.append({
                            "agent": "social",
                            "competitor": name,
                            "platform": "twitter",
                            "error": str(exc),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })

                # Classify each post
                for raw in raw_posts:
                    try:
                        classification = await _classify_post(
                            competitor_name=name,
                            platform=raw["platform"],
                            author=raw["author"],
                            content=raw["content"],
                            likes=raw.get("likes", 0),
                            comments=raw.get("comments", 0),
                            shares=raw.get("shares", 0),
                        )

                        post: SocialPost = {
                            "competitor_name": name,
                            "platform": raw["platform"],
                            "author": raw["author"],
                            "content": raw["content"][:2000],
                            "post_type": classification.get("post_type", "other"),
                            "url": raw.get("url"),
                            "posted_at": raw.get("posted_at"),
                            "likes": raw.get("likes", 0),
                            "comments": raw.get("comments", 0),
                            "shares": raw.get("shares", 0),
                            "engagement_score": float(
                                classification.get("engagement_score", 0.0)
                            ),
                        }
                        all_posts.append(post)
                    except Exception as exc:
                        logger.error("Post classification failed: %s", exc)

        await asyncio.gather(
            *[_process_competitor(comp) for comp in competitors]
        )

    # Sort by engagement score descending
    all_posts.sort(key=lambda p: p["engagement_score"], reverse=True)

    logger.info("Social agent complete: %d posts collected", len(all_posts))

    return {
        "social_posts": all_posts,
        "errors": errors,
    }
