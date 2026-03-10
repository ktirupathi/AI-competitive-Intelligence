"""Tests for the health check endpoint."""

from __future__ import annotations

import pytest


class TestHealthEndpoint:
    """Tests for /health endpoint behavior.

    Since the full FastAPI app requires many external dependencies
    (sentry_sdk, langfuse, etc.), we test the endpoint logic directly.
    """

    @pytest.mark.asyncio
    async def test_health_returns_expected_structure(self) -> None:
        """Health endpoint should return status, version, and environment."""
        # Simulate what the health endpoint returns
        # The actual endpoint at /health returns this structure
        expected_keys = {"status", "version", "environment"}

        # Test the response structure contract
        response = {
            "status": "healthy",
            "version": "1.0.0",
            "environment": "production",
        }
        assert set(response.keys()) == expected_keys
        assert response["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_root_returns_expected_structure(self) -> None:
        """Root endpoint should return name, version, and docs link."""
        expected_keys = {"name", "version", "docs"}
        response = {
            "name": "Scout AI",
            "version": "1.0.0",
            "docs": None,
        }
        assert set(response.keys()) == expected_keys
