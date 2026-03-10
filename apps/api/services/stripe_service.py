"""Service layer for Stripe billing operations."""

import logging
from datetime import datetime, timezone

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()

stripe.api_key = settings.stripe_secret_key

# Plan configuration
PLANS = {
    "starter": {
        "name": "Starter",
        "price_id": settings.stripe_price_starter,
        "price_monthly": 2900,  # $29
        "competitor_limit": 5,
        "features": [
            "5 competitors",
            "Daily monitoring",
            "Email alerts",
            "Weekly briefings",
        ],
    },
    "growth": {
        "name": "Growth",
        "price_id": settings.stripe_price_growth,
        "price_monthly": 7900,  # $79
        "competitor_limit": 15,
        "features": [
            "15 competitors",
            "Real-time monitoring",
            "Slack + Email alerts",
            "Daily briefings",
            "API access",
            "Custom webhooks",
        ],
    },
    "enterprise": {
        "name": "Enterprise",
        "price_id": settings.stripe_price_enterprise,
        "price_monthly": 19900,  # $199
        "competitor_limit": 50,
        "features": [
            "50 competitors",
            "Real-time monitoring",
            "All integrations",
            "Custom briefing schedule",
            "Priority support",
            "SSO",
            "Custom data sources",
        ],
    },
}


class StripeService:
    """Handles Stripe billing operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_customer(self, user: User) -> str:
        """Get or create a Stripe customer for a user."""
        if user.stripe_customer_id:
            return user.stripe_customer_id

        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name,
            metadata={"user_id": str(user.id), "clerk_id": user.clerk_id},
        )

        user.stripe_customer_id = customer.id
        await self.db.flush()
        logger.info("Created Stripe customer %s for user %s", customer.id, user.id)
        return customer.id

    async def create_checkout_session(
        self,
        user: User,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> stripe.checkout.Session:
        """Create a Stripe Checkout session for subscription."""
        customer_id = await self.get_or_create_customer(user)

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": str(user.id)},
            subscription_data={
                "metadata": {"user_id": str(user.id)},
            },
            allow_promotion_codes=True,
        )
        return session

    async def create_portal_session(
        self, user: User, return_url: str
    ) -> stripe.billing_portal.Session:
        """Create a Stripe Customer Portal session."""
        customer_id = await self.get_or_create_customer(user)
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session

    async def get_subscription_status(self, user: User) -> dict:
        """Get the current subscription status for a user."""
        if not user.stripe_subscription_id:
            return {
                "plan": user.plan,
                "status": "active" if user.plan == "free" else "none",
                "current_period_start": None,
                "current_period_end": None,
                "cancel_at_period_end": False,
                "competitor_limit": user.plan_competitor_limit,
            }

        sub = stripe.Subscription.retrieve(user.stripe_subscription_id)
        return {
            "plan": user.plan,
            "status": sub.status,
            "current_period_start": datetime.fromtimestamp(
                sub.current_period_start, tz=timezone.utc
            ),
            "current_period_end": datetime.fromtimestamp(
                sub.current_period_end, tz=timezone.utc
            ),
            "cancel_at_period_end": sub.cancel_at_period_end,
            "competitor_limit": user.plan_competitor_limit,
        }

    async def get_invoices(self, user: User, limit: int = 10) -> list[dict]:
        """List recent invoices for a user."""
        if not user.stripe_customer_id:
            return []

        invoices = stripe.Invoice.list(
            customer=user.stripe_customer_id, limit=limit
        )
        return [
            {
                "id": inv.id,
                "amount_due": inv.amount_due,
                "amount_paid": inv.amount_paid,
                "currency": inv.currency,
                "status": inv.status,
                "invoice_url": inv.hosted_invoice_url,
                "created": datetime.fromtimestamp(inv.created, tz=timezone.utc),
            }
            for inv in invoices.data
        ]

    async def handle_checkout_completed(self, session: dict) -> None:
        """Handle checkout.session.completed webhook event."""
        user_id = session.get("metadata", {}).get("user_id")
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")

        if not user_id or not subscription_id:
            logger.warning("Checkout session missing user_id or subscription_id")
            return

        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            logger.error("User %s not found for checkout", user_id)
            return

        sub = stripe.Subscription.retrieve(subscription_id)
        price_id = sub["items"]["data"][0]["price"]["id"]

        plan_name, plan_config = self._resolve_plan(price_id)

        user.stripe_customer_id = customer_id
        user.stripe_subscription_id = subscription_id
        user.plan = plan_name
        user.plan_competitor_limit = plan_config["competitor_limit"]
        await self.db.flush()
        logger.info("User %s upgraded to %s", user_id, plan_name)

    async def handle_subscription_updated(self, subscription: dict) -> None:
        """Handle customer.subscription.updated webhook event."""
        user_id = subscription.get("metadata", {}).get("user_id")
        if not user_id:
            return

        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return

        price_id = subscription["items"]["data"][0]["price"]["id"]
        plan_name, plan_config = self._resolve_plan(price_id)

        user.plan = plan_name
        user.plan_competitor_limit = plan_config["competitor_limit"]
        user.stripe_subscription_id = subscription["id"]
        await self.db.flush()

    async def handle_subscription_deleted(self, subscription: dict) -> None:
        """Handle customer.subscription.deleted webhook event."""
        user_id = subscription.get("metadata", {}).get("user_id")
        if not user_id:
            return

        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return

        user.plan = "free"
        user.plan_competitor_limit = 3
        user.stripe_subscription_id = None
        await self.db.flush()
        logger.info("User %s downgraded to free plan", user_id)

    def _resolve_plan(self, price_id: str) -> tuple[str, dict]:
        """Resolve a price ID to a plan name and config."""
        for plan_name, config in PLANS.items():
            if config["price_id"] == price_id:
                return plan_name, config
        logger.warning("Unknown price_id: %s, defaulting to starter", price_id)
        return "starter", PLANS["starter"]
