"""Security, rate limiting, and MFA enforcement middleware."""

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

# Endpoint-specific rate limiters: 10 requests per minute
_ENDPOINT_LIMITERS = {
    "/competitors": _TokenBucket(rate=10.0 / 60.0, capacity=10),
    "/briefings": _TokenBucket(rate=10.0 / 60.0, capacity=10),
    "/alerts": _TokenBucket(rate=10.0 / 60.0, capacity=10),
    "/search": _TokenBucket(rate=10.0 / 60.0, capacity=10),
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate-limit incoming requests by client IP.

    Applies per-endpoint limits for /competitors, /briefings, /alerts, /search
    and a global limit for all other endpoints.

    Returns HTTP 429 Too Many Requests when the limit is exceeded.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown"

        path = request.url.path

        # Check auth limiter first
        if "/auth/" in path:
            limiter = _auth_limiter
        else:
            # Check endpoint-specific limiters
            limiter = _global_limiter
            for prefix, endpoint_limiter in _ENDPOINT_LIMITERS.items():
                if prefix in path:
                    if not endpoint_limiter.allow(client_ip):
                        logger.warning(
                            "Endpoint rate limit exceeded for %s on %s",
                            client_ip, path,
                        )
                        return JSONResponse(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            content={"detail": "Too many requests. Please try again later."},
                            headers={"Retry-After": "60"},
                        )
                    break

        if not limiter.allow(client_ip):
            logger.warning("Rate limit exceeded for %s on %s", client_ip, path)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)


class MFAEnforcementMiddleware(BaseHTTPMiddleware):
    """Enforce MFA for authenticated API endpoints.

    Clerk JWTs include MFA verification status. This middleware checks
    for the presence of MFA verification in the token claims for
    sensitive operations.

    Public routes (webhooks, health) are excluded.
    """

    # Paths that do not require MFA
    _EXEMPT_PATHS = {
        "/health",
        "/",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
    }
    _EXEMPT_PREFIXES = (
        "/api/v1/auth/webhook",
        "/api/v1/public/",
    )

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        path = request.url.path

        # Skip MFA check for exempt paths
        if path in self._EXEMPT_PATHS:
            return await call_next(request)
        for prefix in self._EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Only enforce in production
        if settings.environment != "production":
            return await call_next(request)

        # Check for MFA status in Clerk session claims
        # Clerk includes `amr` (Authentication Methods References) in the JWT
        # When MFA is completed, it includes "mfa" in the amr array
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from jose import jwt as jose_jwt
                token = auth_header.removeprefix("Bearer ").strip()
                # Decode without verification just to check claims
                claims = jose_jwt.get_unverified_claims(token)

                # Check Clerk's MFA session metadata
                # Clerk v4+ puts MFA info in session claims
                session_claims = claims.get("session", {})
                factor_verification = session_claims.get(
                    "factor_verification_age", None
                )

                # If Clerk MFA enforcement is enabled and user hasn't completed MFA,
                # the session won't have the appropriate claims.
                # We check if MFA enforcement is configured
                if settings.clerk_enforce_mfa:
                    amr = claims.get("amr", [])
                    if "mfa" not in amr and factor_verification is None:
                        return JSONResponse(
                            status_code=status.HTTP_403_FORBIDDEN,
                            content={
                                "detail": "Multi-factor authentication required. "
                                "Please enable MFA in your account settings."
                            },
                        )
            except Exception:
                # If we can't parse the token, let the auth dependency handle it
                pass

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
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://js.clerk.dev; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.clerk.dev https://*.clerk.accounts.dev; "
            "frame-ancestors 'none'"
        )
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
    app.add_middleware(MFAEnforcementMiddleware)
    app.add_middleware(RateLimitMiddleware)
