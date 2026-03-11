"""Prediction ORM model for competitor strategy forecasting."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competitor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competitors.id", ondelete="SET NULL"),
        index=True,
    )
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("signal_clusters.id", ondelete="SET NULL"),
    )

    prediction: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    timeline: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(100))

    evidence: Mapped[list | None] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(
        String(50), default="active"
    )  # active | confirmed | invalidated | expired
    outcome: Mapped[str | None] = mapped_column(Text)
    extra_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    cluster = relationship("SignalCluster", back_populates="predictions")

    def __repr__(self) -> str:
        return f"<Prediction {self.prediction[:50]}>"
