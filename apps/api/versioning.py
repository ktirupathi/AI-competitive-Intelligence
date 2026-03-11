"""API versioning utilities.

Provides middleware that adds version-related headers and supports
future deprecation of older API versions.

Current version: v1 (stable)
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Current stable API version
CURRENT_VERSION = "v1"

# Deprecated versions and their sunset dates (ISO-8601)
# When a version is added here, responses on that prefix include
# a Deprecation + Sunset header per IETF draft-ietf-httpapi-deprecation-header.
DEPRECATED_VERSIONS: dict[str, str] = {
    # Example: "v0": "2025-06-01",
}


class APIVersionHeaderMiddleware(BaseHTTPMiddleware):
    """Inject API-Version and deprecation headers into responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        path = request.url.path

        # Detect version prefix (e.g. /api/v1/...)
        for prefix in ("/api/v",):
            idx = path.find(prefix)
            if idx != -1:
                # Extract version segment (e.g. "v1")
                after = path[idx + len("/api/") :]
                version = after.split("/", 1)[0]
                response.headers["X-API-Version"] = version

                if version in DEPRECATED_VERSIONS:
                    sunset = DEPRECATED_VERSIONS[version]
                    response.headers["Deprecation"] = "true"
                    response.headers["Sunset"] = sunset
                    response.headers["Link"] = (
                        f'</api/{CURRENT_VERSION}>; rel="successor-version"'
                    )
                break

        return response
