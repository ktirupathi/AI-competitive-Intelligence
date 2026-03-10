"""AI-generated insight ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    competitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competitors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # strategy | product | pricing | marketing | hiring | sentiment
    severity: Mapped[str] = mapped_column(
        String(20), default="medium"
    )  # low | medium | high | critical
    confidence: Mapped[float] = mapped_column(Float, default=0.8)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    recommended_action: Mapped[str | None] = mapped_column(Text)

    # Source references (change IDs, news IDs, etc.)
    source_refs: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    is_read: Mapped[bool] = mapped_column(default=False)
    is_dismissed: Mapped[bool] = mapped_column(default=False)

    # Public sharing
    is_public: Mapped[bool] = mapped_column(default=False)
    public_token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    competitor = relationship("Competitor", back_populates="insights")

    def __repr__(self) -> str:
        return f"<Insight {self.category}: {self.title[:40]}>"
