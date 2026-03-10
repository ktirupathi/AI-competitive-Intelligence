"""User integration configuration ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # slack | email | webhook
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Slack-specific
    slack_channel_id: Mapped[str | None] = mapped_column(String(255))
    slack_workspace_id: Mapped[str | None] = mapped_column(String(255))
    slack_access_token: Mapped[str | None] = mapped_column(Text)  # encrypted in practice

    # Email-specific
    email_address: Mapped[str | None] = mapped_column(String(320))

    # Webhook-specific
    webhook_url: Mapped[str | None] = mapped_column(Text)
    webhook_secret: Mapped[str | None] = mapped_column(String(255))

    # What events to deliver
    event_filters: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # Configuration metadata
    config: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="integrations")

    def __repr__(self) -> str:
        return f"<Integration {self.type} for user {self.user_id}>"
