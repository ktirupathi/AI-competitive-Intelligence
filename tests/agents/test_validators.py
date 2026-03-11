"""Tests for data validators."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agents.validators import (
    validate_job_posting,
    validate_news_item,
    validate_review,
    validate_social_post,
    validate_web_snapshot,
)


class TestValidateWebSnapshot:

    def test_valid_content(self) -> None:
        content = "A" * 600
        valid, reason = validate_web_snapshot(content)
        assert valid is True

    def test_empty_content(self) -> None:
        valid, reason = validate_web_snapshot("")
        assert valid is False
        assert "Empty" in reason

    def test_too_short(self) -> None:
        valid, reason = validate_web_snapshot("Short text")
        assert valid is False
        assert "too short" in reason

    def test_detects_captcha_page(self) -> None:
        # Content must be >500 chars to pass length check but <3000 to trigger bot detection
        content = ("Please verify you are a human. Complete the CAPTCHA below. " * 15)
        valid, reason = validate_web_snapshot(content)
        assert valid is False
        assert "bot detection" in reason.lower() or "captcha" in reason.lower()

    def test_detects_cloudflare_challenge(self) -> None:
        content = "Checking your browser before accessing the site. Just a moment..."
        valid, reason = validate_web_snapshot(content)
        assert valid is False

    def test_detects_access_denied(self) -> None:
        content = "403 Forbidden. Access Denied. Your IP has been blocked."
        valid, reason = validate_web_snapshot(content)
        assert valid is False

    def test_long_page_with_cloudflare_mention_passes(self) -> None:
        # A long legitimate page that mentions Cloudflare should pass
        content = "x" * 3500 + " We use Cloudflare for CDN. " + "x" * 500
        valid, reason = validate_web_snapshot(content)
        assert valid is True


class TestValidateNewsItem:

    def test_valid_item(self) -> None:
        item = {
            "title": "Acme Corp raises funding",
            "url": "https://techcrunch.com/acme",
            "date": datetime.now(timezone.utc).isoformat(),
        }
        valid, reason = validate_news_item(item)
        assert valid is True

    def test_missing_title(self) -> None:
        item = {"title": "", "url": "https://example.com"}
        valid, reason = validate_news_item(item)
        assert valid is False
        assert "title" in reason.lower()

    def test_missing_url(self) -> None:
        item = {"title": "Title", "url": ""}
        valid, reason = validate_news_item(item)
        assert valid is False

    def test_invalid_url(self) -> None:
        item = {"title": "Title", "url": "not-a-url"}
        valid, reason = validate_news_item(item)
        assert valid is False
        assert "Invalid URL" in reason

    def test_old_article_rejected(self) -> None:
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
        item = {"title": "Old news", "url": "https://example.com/old", "date": old_date}
        valid, reason = validate_news_item(item, lookback_days=30)
        assert valid is False
        assert "too old" in reason.lower()

    def test_recent_article_passes(self) -> None:
        recent = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
        item = {"title": "Recent", "url": "https://example.com/recent", "date": recent}
        valid, reason = validate_news_item(item, lookback_days=30)
        assert valid is True

    def test_unparseable_date_passes(self) -> None:
        item = {"title": "Title", "url": "https://example.com", "date": "sometime"}
        valid, reason = validate_news_item(item)
        assert valid is True  # Don't reject for unparseable dates


class TestValidateReview:

    def test_valid_review(self) -> None:
        review = {"title": "Great product", "text": "Very useful tool", "rating": 4.5}
        valid, reason = validate_review(review)
        assert valid is True

    def test_missing_title_and_text(self) -> None:
        valid, reason = validate_review({"title": "", "text": ""})
        assert valid is False

    def test_rating_out_of_range(self) -> None:
        review = {"title": "Bad", "text": "Text", "rating": 6.0}
        valid, reason = validate_review(review)
        assert valid is False
        assert "out of range" in reason

    def test_negative_rating(self) -> None:
        review = {"title": "Bad", "text": "Text", "rating": -1}
        valid, reason = validate_review(review)
        assert valid is False

    def test_placeholder_text(self) -> None:
        review = {"title": "Test", "text": "Lorem ipsum dolor sit amet", "rating": 3}
        valid, reason = validate_review(review)
        assert valid is False
        assert "placeholder" in reason.lower()

    def test_no_rating_is_ok(self) -> None:
        review = {"title": "Just a title", "text": "Some review text"}
        valid, reason = validate_review(review)
        assert valid is True


class TestValidateSocialPost:

    def test_valid_post(self) -> None:
        post = {"content": "Exciting announcement!", "platform": "linkedin", "likes": 100}
        valid, reason = validate_social_post(post)
        assert valid is True

    def test_missing_content(self) -> None:
        valid, reason = validate_social_post({"content": "", "platform": "twitter"})
        assert valid is False

    def test_missing_platform(self) -> None:
        valid, reason = validate_social_post({"content": "Hello", "platform": ""})
        assert valid is False

    def test_negative_likes(self) -> None:
        post = {"content": "Post", "platform": "twitter", "likes": -5}
        valid, reason = validate_social_post(post)
        assert valid is False
        assert "Negative" in reason


class TestValidateJobPosting:

    def test_valid_posting(self) -> None:
        valid, reason = validate_job_posting({"title": "Senior Engineer"})
        assert valid is True

    def test_missing_title(self) -> None:
        valid, reason = validate_job_posting({"title": ""})
        assert valid is False

    def test_title_too_short(self) -> None:
        valid, reason = validate_job_posting({"title": "Dev"})
        assert valid is False

    def test_duplicate_detection(self) -> None:
        seen: set[str] = set()
        valid1, _ = validate_job_posting({"title": "Software Engineer"}, seen)
        assert valid1 is True
        valid2, reason = validate_job_posting({"title": "Software Engineer"}, seen)
        assert valid2 is False
        assert "Duplicate" in reason

    def test_case_insensitive_dedup(self) -> None:
        seen: set[str] = set()
        validate_job_posting({"title": "Software Engineer"}, seen)
        valid, _ = validate_job_posting({"title": "software engineer"}, seen)
        assert valid is False
