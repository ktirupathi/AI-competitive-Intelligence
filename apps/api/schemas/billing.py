"""Pydantic schemas for billing and subscriptions."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class SubscriptionStatus(BaseModel):
    plan: str
    status: str  # active | canceled | past_due | trialing
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    competitor_limit: int
    competitors_used: int


class CreateCheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str


class CreateCheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class CreatePortalRequest(BaseModel):
    return_url: str


class CreatePortalResponse(BaseModel):
    portal_url: str


class PlanInfo(BaseModel):
    name: str
    price_id: str
    price_monthly: int  # cents
    competitor_limit: int
    features: list[str]


class PlanListResponse(BaseModel):
    plans: list[PlanInfo]


class InvoiceRead(BaseModel):
    id: str
    amount_due: int
    amount_paid: int
    currency: str
    status: str
    invoice_url: str | None = None
    created: datetime


class InvoiceListResponse(BaseModel):
    invoices: list[InvoiceRead]
