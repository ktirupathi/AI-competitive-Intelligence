"""Security and rate limiting middleware for the FastAPI application."""

import logging
import time
from typing import Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# In-memory rate limiter (use Redis in production for multi-process)
# ---------------------------------------------------------------------------
class _TokenBucket:
    """Simple token-bucket rate limiter."""

    def __init__(self, rate: float, capacity: int) -> None:
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self._tokens: dict[str, float] = {}
        self._last_time: dict[str, float] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        tokens = self._tokens.get(key, self.capacity)
        last = self._last_time.get(key, now)

        elapsed = now - last
        tokens = min(self.capacity, tokens + elapsed * self.rate)

        if tokens >= 1:
            self._tokens[key] = tokens - 1
            self._last_time[key] = now
            return True

        self._tokens[key] = tokens
        self._last_time[key] = now
        return False


# Default: 60 requests per minute per IP
_global_limiter = _TokenBucket(rate=1.0, capacity=60)

# Stricter limit for auth endpoints: 10 requests per minute per IP
_auth_limiter = _TokenBucket(rate=10.0 / 60.0, capacity=10)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate-limit incoming requests by client IP.

    Returns HTTP 429 Too Many Requests when the limit is exceeded.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown"

        # Use stricter limiter for auth endpoints
        path = request.url.path
        if "/auth/" in path:
            limiter = _auth_limiter
        else:
            limiter = _global_limiter

        if not limiter.allow(client_ip):
            logger.warning("Rate limit exceeded for %s on %s", client_ip, path)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard security headers to all responses."""

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request method, path, status, and latency."""

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Skip health check spam
        if request.url.path in ("/health", "/"):
            return response

        logger.info(
            "%s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response


def register_middleware(app: FastAPI) -> None:
    """Register all custom middleware on the FastAPI app.

    Call order matters: outermost middleware is added first.
    """
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
