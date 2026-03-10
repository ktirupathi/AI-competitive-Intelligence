"""Unified scraping service for all agents and tasks.

Provides a single entry point for web scraping using Firecrawl (preferred)
with httpx as a fallback. Handles rate limiting, retries, and content
normalization.
"""

import hashlib
import logging
import re
from typing import Any

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Re-usable headers for direct HTTP requests
_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ScoutAI/1.0; +https://scoutai.app)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class ScrapingService:
    """Async web scraping with Firecrawl + httpx fallback."""

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self._firecrawl_key = settings.firecrawl_api_key
        self._firecrawl_base = "https://api.firecrawl.dev/v1"

    async def crawl_url(
        self,
        url: str,
        *,
        only_main_content: bool = True,
        formats: list[str] | None = None,
    ) -> dict[str, Any]:
        """Crawl a URL and return structured result.

        Returns:
            {
                "url": str,
                "content": str (markdown or raw HTML),
                "content_hash": str (SHA-256 of normalized content),
                "status_code": int,
                "source": "firecrawl" | "httpx",
            }
        """
        if formats is None:
            formats = ["markdown"]

        # Try Firecrawl first
        if self._firecrawl_key:
            try:
                result = await self._crawl_firecrawl(url, only_main_content, formats)
                if result["content"]:
                    return result
            except Exception as exc:
                logger.warning("Firecrawl failed for %s, falling back to httpx: %s", url, exc)

        # Fallback to direct HTTP
        return await self._crawl_httpx(url)

    async def _crawl_firecrawl(
        self,
        url: str,
        only_main_content: bool,
        formats: list[str],
    ) -> dict[str, Any]:
        """Scrape via the Firecrawl API."""
        headers = {
            "Authorization": f"Bearer {self._firecrawl_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "url": url,
            "formats": formats,
            "onlyMainContent": only_main_content,
            "timeout": int(self.timeout * 1000),
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._firecrawl_base}/scrape",
                json=payload,
                headers=headers,
                timeout=self.timeout + 10,
            )
            resp.raise_for_status()
            data = resp.json()

        content = data.get("data", {}).get("markdown", "")
        status_code = data.get("data", {}).get("metadata", {}).get("statusCode", 200)

        return {
            "url": url,
            "content": content,
            "content_hash": self._hash_content(content),
            "status_code": status_code,
            "source": "firecrawl",
        }

    async def _crawl_httpx(self, url: str) -> dict[str, Any]:
        """Fallback scraper using plain httpx."""
        async with httpx.AsyncClient(
            follow_redirects=True, headers=_DEFAULT_HEADERS
        ) as client:
            resp = await client.get(url, timeout=self.timeout)
            resp.raise_for_status()

        content = resp.text
        return {
            "url": url,
            "content": content,
            "content_hash": self._hash_content(content),
            "status_code": resp.status_code,
            "source": "httpx",
        }

    @staticmethod
    def extract_text(html: str) -> str:
        """Extract visible text from raw HTML, stripping tags and scripts.

        For best results, feed this Firecrawl's markdown output instead.
        """
        # Remove script and style blocks
        cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        # Collapse whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @staticmethod
    def normalize_content(text: str) -> str:
        """Normalize content for consistent hashing and comparison.

        Lowercases, collapses whitespace, strips common boilerplate markers.
        """
        normalized = text.lower()
        normalized = re.sub(r"\s+", " ", normalized).strip()
        # Remove common dynamic content that changes every page load
        normalized = re.sub(r"©\s*\d{4}", "", normalized)
        normalized = re.sub(r"all rights reserved\.?", "", normalized, flags=re.IGNORECASE)
        return normalized

    @staticmethod
    def _hash_content(text: str) -> str:
        """SHA-256 hash of normalized content."""
        normalized = " ".join(text.split()).strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
