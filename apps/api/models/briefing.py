"""Weekly briefing ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Briefing(Base):
    __tablename__ = "briefings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    frequency: Mapped[str] = mapped_column(
        String(20), default="weekly"
    )  # daily | weekly | monthly

    # The actual briefing content (markdown)
    executive_summary: Mapped[str | None] = mapped_column(Text)
    full_content: Mapped[str | None] = mapped_column(Text)

    # Structured sections
    sections: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # Period covered
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Delivery status
    status: Mapped[str] = mapped_column(
        String(20), default="draft"
    )  # draft | generated | sent | failed
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_channels: Mapped[list | None] = mapped_column(JSONB, default=list)

    # Stats
    competitor_count: Mapped[int] = mapped_column(default=0)
    insight_count: Mapped[int] = mapped_column(default=0)
    change_count: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="briefings")

    def __repr__(self) -> str:
        return f"<Briefing {self.title}>"
