"""Signal cluster ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class SignalCluster(Base):
    __tablename__ = "signal_clusters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cluster_title: Mapped[str] = mapped_column(String(500), nullable=False)
    cluster_description: Mapped[str | None] = mapped_column(Text)

    confidence_score: Mapped[float] = mapped_column(Float, default=0.5)
    impact_score: Mapped[float] = mapped_column(Float, default=0.5)
    signal_count: Mapped[int] = mapped_column(Integer, default=0)

    source_types: Mapped[list | None] = mapped_column(JSONB, default=list)
    related_signal_ids: Mapped[list | None] = mapped_column(JSONB, default=list)
    metadata: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    predictions = relationship(
        "Prediction", back_populates="cluster", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<SignalCluster {self.cluster_title[:40]}>"
