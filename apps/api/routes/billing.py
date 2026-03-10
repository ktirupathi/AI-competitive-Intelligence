"""Billing routes: Stripe webhooks and subscription management."""

import logging

import stripe
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select

from ..config import get_settings
from ..deps import CurrentUser, DbSession
from ..models.competitor import Competitor
from ..schemas.billing import (
    CreateCheckoutRequest,
    CreateCheckoutResponse,
    CreatePortalRequest,
    CreatePortalResponse,
    InvoiceListResponse,
    PlanInfo,
    PlanListResponse,
    SubscriptionStatus,
)
from ..services.stripe_service import PLANS, StripeService

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.get("/plans", response_model=PlanListResponse)
async def list_plans() -> PlanListResponse:
    """List available subscription plans."""
    plans = [
        PlanInfo(
            name=config["name"],
            price_id=config["price_id"],
            price_monthly=config["price_monthly"],
            competitor_limit=config["competitor_limit"],
            features=config["features"],
        )
        for config in PLANS.values()
    ]
    return PlanListResponse(plans=plans)


@router.get("/subscription", response_model=SubscriptionStatus)
async def get_subscription(
    db: DbSession,
    user: CurrentUser,
) -> SubscriptionStatus:
    """Get the current user's subscription status."""
    service = StripeService(db)
    status_data = await service.get_subscription_status(user)

    # Count current competitors
    count_q = select(func.count()).where(Competitor.user_id == user.id)
    competitors_used = (await db.execute(count_q)).scalar() or 0
    status_data["competitors_used"] = competitors_used

    return SubscriptionStatus(**status_data)


@router.post("/checkout", response_model=CreateCheckoutResponse)
async def create_checkout(
    data: CreateCheckoutRequest,
    db: DbSession,
    user: CurrentUser,
) -> CreateCheckoutResponse:
    """Create a Stripe Checkout session for subscribing to a plan."""
    service = StripeService(db)
    try:
        session = await service.create_checkout_session(
            user=user,
            price_id=data.price_id,
            success_url=data.success_url,
            cancel_url=data.cancel_url,
        )
    except stripe.StripeError as exc:
        logger.error("Stripe checkout error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {exc.user_message or str(exc)}",
        )
    await db.commit()
    return CreateCheckoutResponse(
        checkout_url=session.url,
        session_id=session.id,
    )


@router.post("/portal", response_model=CreatePortalResponse)
async def create_portal(
    data: CreatePortalRequest,
    db: DbSession,
    user: CurrentUser,
) -> CreatePortalResponse:
    """Create a Stripe Customer Portal session for managing billing."""
    service = StripeService(db)
    try:
        session = await service.create_portal_session(
            user=user,
            return_url=data.return_url,
        )
    except stripe.StripeError as exc:
        logger.error("Stripe portal error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {exc.user_message or str(exc)}",
        )
    await db.commit()
    return CreatePortalResponse(portal_url=session.url)


@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    db: DbSession,
    user: CurrentUser,
) -> InvoiceListResponse:
    """List the current user's invoices."""
    service = StripeService(db)
    try:
        invoices = await service.get_invoices(user)
    except stripe.StripeError as exc:
        logger.error("Stripe invoices error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {exc.user_message or str(exc)}",
        )
    return InvoiceListResponse(invoices=invoices)


@router.post("/webhook/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    db: DbSession,
) -> dict[str, str]:
    """Handle Stripe webhook events.

    Supported events:
    - checkout.session.completed
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_failed
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature header",
        )

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    service = StripeService(db)
    event_type = event["type"]
    data_object = event["data"]["object"]

    try:
        if event_type == "checkout.session.completed":
            await service.handle_checkout_completed(data_object)
        elif event_type == "customer.subscription.updated":
            await service.handle_subscription_updated(data_object)
        elif event_type == "customer.subscription.deleted":
            await service.handle_subscription_deleted(data_object)
        elif event_type == "invoice.payment_failed":
            logger.warning(
                "Payment failed for customer %s",
                data_object.get("customer"),
            )
        else:
            logger.debug("Unhandled Stripe event: %s", event_type)
    except Exception:
        logger.exception("Error handling Stripe webhook event %s", event_type)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing error",
        )

    await db.commit()
    return {"status": "ok", "event": event_type}
