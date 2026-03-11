"""Tests for briefing API routes.

Tests schema validation and structure for briefing-related endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from apps.api.schemas.briefing import (
    BriefingGenerateRequest,
    BriefingListResponse,
    BriefingRead,
)


class TestBriefingSchemas:
    """Tests for briefing Pydantic schemas."""

    def test_generate_request_with_competitor_ids(self) -> None:
        req = BriefingGenerateRequest(
            competitor_ids=[uuid.uuid4(), uuid.uuid4()],
        )
        assert len(req.competitor_ids) == 2

    def test_list_response_structure(self) -> None:
        response = BriefingListResponse(items=[], total=0)
        assert response.total == 0
        assert response.items == []

    def test_briefing_read_from_attributes(self) -> None:
        """BriefingRead should support from_attributes mode."""
        assert BriefingRead.model_config.get("from_attributes") is True
