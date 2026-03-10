"""User ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    clerk_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    full_name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    company_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Subscription / billing
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255))
    plan: Mapped[str] = mapped_column(
        String(50), default="free"
    )  # free | starter | growth | enterprise
    plan_competitor_limit: Mapped[int] = mapped_column(default=3)

    # Notification preferences stored as JSON
    notification_prefs: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # Settings
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    briefing_frequency: Mapped[str] = mapped_column(
        String(20), default="weekly"
    )  # daily | weekly | monthly

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    competitors = relationship(
        "Competitor", back_populates="user", cascade="all, delete-orphan"
    )
    briefings = relationship(
        "Briefing", back_populates="user", cascade="all, delete-orphan"
    )
    integrations = relationship(
        "Integration", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
