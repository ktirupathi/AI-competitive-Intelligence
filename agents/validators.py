"""
Scout AI - Data Validators

Validation functions for scraped content to detect bot detection pages,
invalid data, and ensure quality before processing. Each validator returns
a tuple of (is_valid, reason).
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Common CAPTCHA and bot-detection indicators
_BOT_DETECTION_PATTERNS = [
    r"captcha",
    r"recaptcha",
    r"hcaptcha",
    r"cf-challenge",
    r"cloudflare",
    r"access\s+denied",
    r"403\s+forbidden",
    r"please\s+verify\s+you\s+are\s+(?:a\s+)?human",
    r"bot\s+detection",
    r"unusual\s+traffic",
    r"blocked\s+your\s+(?:ip|request)",
    r"enable\s+javascript",
    r"checking\s+your\s+browser",
    r"just\s+a\s+moment",
    r"ray\s+id",
]
_BOT_REGEX = re.compile("|".join(_BOT_DETECTION_PATTERNS), re.IGNORECASE)

_MIN_CONTENT_LENGTH = 500


def validate_web_snapshot(content: str) -> tuple[bool, str]:
    """Validate scraped web content for quality.

    Checks for:
    - Bot detection / CAPTCHA pages
    - Minimum content length (>500 chars)
    - Empty body detection
    """
    if not content or not content.strip():
        return False, "Empty content"

    stripped = content.strip()
    if len(stripped) < _MIN_CONTENT_LENGTH:
        return False, f"Content too short ({len(stripped)} chars, min {_MIN_CONTENT_LENGTH})"

    # Check for bot detection indicators
    match = _BOT_REGEX.search(stripped[:5000])
    if match:
        indicator = match.group(0)
        # Only flag if the page is mostly bot-detection (short + bot indicators)
        if len(stripped) < 3000:
            return False, f"Likely bot detection page (found: '{indicator}')"

    return True, "valid"


def validate_news_item(item: dict[str, Any], lookback_days: int = 30) -> tuple[bool, str]:
    """Validate a news search result item.

    Checks for:
    - Required fields (title, url)
    - Valid URL format
    - Date is parseable and within lookback window
    """
    title = item.get("title", "").strip()
    if not title:
        return False, "Missing title"

    url = item.get("url", "").strip()
    if not url:
        return False, "Missing URL"

    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False, f"Invalid URL: {url}"
    except Exception:
        return False, f"Unparseable URL: {url}"

    date_str = item.get("date") or item.get("published_at")
    if date_str:
        try:
            dt = _parse_date(date_str)
            if dt:
                cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
                if dt < cutoff:
                    return False, f"Article too old ({date_str}), cutoff={lookback_days} days"
        except (ValueError, TypeError):
            pass  # Unparseable date is not a rejection reason

    return True, "valid"


def validate_review(review: dict[str, Any]) -> tuple[bool, str]:
    """Validate an extracted review.

    Checks for:
    - Required fields (title or text)
    - Rating in valid range (0-5)
    - Non-empty/placeholder text
    """
    title = review.get("title", "").strip()
    text = review.get("text", "").strip()

    if not title and not text:
        return False, "Missing both title and text"

    rating = review.get("rating")
    if rating is not None:
        try:
            rating_f = float(rating)
            if rating_f < 0 or rating_f > 5:
                return False, f"Rating out of range: {rating_f}"
        except (ValueError, TypeError):
            return False, f"Invalid rating value: {rating}"

    # Check for placeholder text
    placeholder_patterns = [
        r"^lorem ipsum",
        r"^test\s+review",
        r"^placeholder",
        r"^n/a$",
    ]
    for pattern in placeholder_patterns:
        if text and re.match(pattern, text, re.IGNORECASE):
            return False, f"Placeholder text detected"

    return True, "valid"


def validate_social_post(post: dict[str, Any]) -> tuple[bool, str]:
    """Validate a scraped social media post.

    Checks for:
    - Required fields (content, platform)
    - Engagement metrics are non-negative numbers
    """
    content = post.get("content", "").strip()
    if not content:
        return False, "Missing content"

    platform = post.get("platform", "").strip()
    if not platform:
        return False, "Missing platform"

    # Validate engagement metrics
    for metric in ("likes", "comments", "shares"):
        value = post.get(metric, 0)
        if value is not None:
            try:
                v = int(value)
                if v < 0:
                    return False, f"Negative {metric}: {v}"
            except (ValueError, TypeError):
                return False, f"Invalid {metric} value: {value}"

    return True, "valid"


def validate_job_posting(
    posting: dict[str, Any],
    seen_titles: set[str] | None = None,
) -> tuple[bool, str]:
    """Validate an extracted job posting.

    Checks for:
    - Required fields (title)
    - Duplicate detection via title hash
    """
    title = posting.get("title", "").strip()
    if not title:
        return False, "Missing title"

    if len(title) < 5:
        return False, f"Title too short: '{title}'"

    # Check for duplicates
    if seen_titles is not None:
        title_key = title.lower().strip()
        if title_key in seen_titles:
            return False, f"Duplicate posting: '{title}'"
        seen_titles.add(title_key)

    return True, "valid"


def _parse_date(date_str: str) -> datetime | None:
    """Try to parse a date string in common formats."""
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None
