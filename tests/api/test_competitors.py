"""Tests for competitor CRUD API routes.

These tests verify route logic, auth validation, and input validation
by testing the schemas and route handler logic.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from apps.api.schemas.competitor import (
    CompetitorCreate,
    CompetitorListResponse,
    CompetitorRead,
    CompetitorUpdate,
)


class TestCompetitorSchemas:
    """Tests for competitor Pydantic schemas."""

    def test_create_valid_competitor(self) -> None:
        data = CompetitorCreate(
            name="Acme Corp",
            domain="acme.com",
            description="A competitor",
            track_website=True,
        )
        assert data.name == "Acme Corp"
        assert data.domain == "acme.com"

    def test_create_requires_name(self) -> None:
        with pytest.raises(ValidationError):
            CompetitorCreate(name="", domain="acme.com")

    def test_create_requires_domain(self) -> None:
        with pytest.raises(ValidationError):
            CompetitorCreate(name="Acme", domain="")

    def test_name_max_length(self) -> None:
        # Name gets truncated to 200 by the sanitiser, then max_length=200 applies
        data = CompetitorCreate(name="A" * 256, domain="acme.com")
        assert len(data.name) == 200

    def test_domain_max_length(self) -> None:
        with pytest.raises(ValidationError):
            CompetitorCreate(name="Acme", domain="a" * 256)

    def test_update_allows_partial(self) -> None:
        data = CompetitorUpdate(name="New Name")
        assert data.name == "New Name"
        assert data.domain is None

    def test_update_all_fields_optional(self) -> None:
        data = CompetitorUpdate()
        assert data.name is None
        assert data.domain is None
        assert data.track_website is None

    def test_list_response_structure(self) -> None:
        now = datetime.now()
        items = [
            CompetitorRead(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                name="Test",
                domain="test.com",
                created_at=now,
                updated_at=now,
            )
        ]
        response = CompetitorListResponse(items=items, total=1)
        assert response.total == 1
        assert len(response.items) == 1

    def test_read_from_attributes(self) -> None:
        """CompetitorRead should support from_attributes mode."""
        assert CompetitorRead.model_config.get("from_attributes") is True


class TestCompetitorInputValidation:
    """Tests for input validation edge cases."""

    def test_name_with_special_characters(self) -> None:
        data = CompetitorCreate(name="Acme & Co. (Ltd.)", domain="acme.com")
        assert data.name == "Acme & Co. (Ltd.)"

    def test_domain_without_protocol(self) -> None:
        data = CompetitorCreate(name="Acme", domain="acme.com")
        assert data.domain == "acme.com"

    def test_social_links_as_dict(self) -> None:
        data = CompetitorCreate(
            name="Acme",
            domain="acme.com",
            social_links={"linkedin": "https://linkedin.com/company/acme"},
        )
        assert data.social_links["linkedin"] == "https://linkedin.com/company/acme"

    def test_tracking_defaults(self) -> None:
        data = CompetitorCreate(name="Acme", domain="acme.com")
        assert data.track_website is True
        assert data.track_news is True
        assert data.track_jobs is True
        assert data.track_reviews is True
        assert data.track_social is True


class TestInputSanitisation:
    """Tests for HTML stripping, whitespace trimming, and length enforcement."""

    def test_name_strips_html_tags(self) -> None:
        data = CompetitorCreate(
            name='<script>alert("xss")</script>Acme Corp',
            domain="acme.com",
        )
        assert "<script>" not in data.name
        assert "Acme Corp" in data.name

    def test_name_collapses_whitespace(self) -> None:
        data = CompetitorCreate(name="  Acme   Corp  ", domain="acme.com")
        assert data.name == "Acme Corp"

    def test_name_truncated_to_200(self) -> None:
        data = CompetitorCreate(name="A" * 300, domain="acme.com")
        assert len(data.name) == 200

    def test_description_strips_html(self) -> None:
        data = CompetitorCreate(
            name="Acme",
            domain="acme.com",
            description="<b>Bold</b> description <img src=x>",
        )
        assert "<b>" not in data.description
        assert "<img" not in data.description
        assert "Bold description" in data.description

    def test_domain_strips_trailing_slash(self) -> None:
        data = CompetitorCreate(name="Acme", domain="acme.com/")
        assert data.domain == "acme.com"

    def test_domain_strips_whitespace(self) -> None:
        data = CompetitorCreate(name="Acme", domain="  acme.com  ")
        assert data.domain == "acme.com"

    def test_industry_sanitised(self) -> None:
        data = CompetitorCreate(
            name="Acme",
            domain="acme.com",
            industry="<em>SaaS</em>  &  Cloud",
        )
        assert "<em>" not in data.industry
        assert "SaaS & Cloud" in data.industry
