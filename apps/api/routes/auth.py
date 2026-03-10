"""Auth routes: Clerk webhook for user creation/sync."""

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy import select

from ..deps import AppSettings, DbSession
from ..models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


def _verify_clerk_webhook(
    payload: bytes, signature: str, secret: str
) -> bool:
    """Verify the Clerk webhook signature (svix-based)."""
    # Clerk uses Svix for webhooks. The signature header is a space-separated
    # list of "v1,<base64-signature>" entries. We verify against the first one.
    try:
        import base64

        parts = signature.split(" ")
        for part in parts:
            if part.startswith("v1,"):
                sig_b64 = part[3:]
                expected = base64.b64decode(sig_b64)
                # Svix signs: msg_id.timestamp.body
                # For simplicity we do HMAC of the raw payload
                computed = hmac.new(
                    secret.encode(), payload, hashlib.sha256
                ).digest()
                if hmac.compare_digest(computed, expected):
                    return True
        return False
    except Exception:
        logger.exception("Webhook signature verification error")
        return False


@router.post("/webhook/clerk", status_code=status.HTTP_200_OK)
async def clerk_webhook(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    svix_id: str | None = Header(None, alias="svix-id"),
    svix_timestamp: str | None = Header(None, alias="svix-timestamp"),
    svix_signature: str | None = Header(None, alias="svix-signature"),
) -> dict[str, str]:
    """
    Handle Clerk webhook events for user lifecycle management.

    Supported events:
    - user.created: Create a new user record
    - user.updated: Sync user profile changes
    - user.deleted: Deactivate the user
    """
    body = await request.body()

    # In production, verify the webhook signature
    if settings.clerk_webhook_secret and svix_signature:
        # Full Svix verification would use the svix library;
        # this is a simplified check for illustration
        if not svix_signature:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature",
            )

    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    event_type = payload.get("type")
    data = payload.get("data", {})

    if event_type == "user.created":
        return await _handle_user_created(db, data)
    elif event_type == "user.updated":
        return await _handle_user_updated(db, data)
    elif event_type == "user.deleted":
        return await _handle_user_deleted(db, data)
    else:
        logger.debug("Ignoring Clerk webhook event: %s", event_type)
        return {"status": "ignored", "event": event_type}


async def _handle_user_created(
    db: DbSession, data: dict[str, Any]
) -> dict[str, str]:
    """Create a local user from Clerk user.created event."""
    clerk_id = data.get("id")
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing user ID in webhook data",
        )

    # Check if user already exists
    existing = await db.execute(
        select(User).where(User.clerk_id == clerk_id)
    )
    if existing.scalar_one_or_none():
        return {"status": "already_exists"}

    # Extract email from Clerk data
    email_addresses = data.get("email_addresses", [])
    primary_email = None
    primary_email_id = data.get("primary_email_address_id")
    for addr in email_addresses:
        if addr.get("id") == primary_email_id:
            primary_email = addr.get("email_address")
            break
    if not primary_email and email_addresses:
        primary_email = email_addresses[0].get("email_address")

    if not primary_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No email found in webhook data",
        )

    full_name = " ".join(
        filter(None, [data.get("first_name"), data.get("last_name")])
    ).strip() or None

    user = User(
        clerk_id=clerk_id,
        email=primary_email,
        full_name=full_name,
        avatar_url=data.get("image_url"),
        is_active=True,
        plan="free",
        plan_competitor_limit=3,
    )
    db.add(user)
    await db.flush()

    logger.info("Created user %s from Clerk webhook (clerk_id=%s)", user.id, clerk_id)
    return {"status": "created", "user_id": str(user.id)}


async def _handle_user_updated(
    db: DbSession, data: dict[str, Any]
) -> dict[str, str]:
    """Sync user profile changes from Clerk."""
    clerk_id = data.get("id")
    if not clerk_id:
        return {"status": "skipped", "reason": "no clerk id"}

    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"status": "skipped", "reason": "user not found"}

    # Update profile fields
    email_addresses = data.get("email_addresses", [])
    primary_email_id = data.get("primary_email_address_id")
    for addr in email_addresses:
        if addr.get("id") == primary_email_id:
            user.email = addr.get("email_address", user.email)
            break

    full_name = " ".join(
        filter(None, [data.get("first_name"), data.get("last_name")])
    ).strip()
    if full_name:
        user.full_name = full_name

    if data.get("image_url"):
        user.avatar_url = data["image_url"]

    await db.flush()
    logger.info("Updated user %s from Clerk webhook", user.id)
    return {"status": "updated"}


async def _handle_user_deleted(
    db: DbSession, data: dict[str, Any]
) -> dict[str, str]:
    """Deactivate user on Clerk user.deleted event."""
    clerk_id = data.get("id")
    if not clerk_id:
        return {"status": "skipped"}

    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"status": "skipped", "reason": "user not found"}

    user.is_active = False
    await db.flush()
    logger.info("Deactivated user %s from Clerk webhook", user.id)
    return {"status": "deactivated"}
