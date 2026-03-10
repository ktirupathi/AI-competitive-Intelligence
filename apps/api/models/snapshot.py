"""Website snapshot ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    competitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competitors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    page_type: Mapped[str] = mapped_column(
        String(50), default="homepage"
    )  # homepage | pricing | product | blog | careers
    content_hash: Mapped[str | None] = mapped_column(String(64))
    raw_html: Mapped[str | None] = mapped_column(Text)
    markdown_content: Mapped[str | None] = mapped_column(Text)
    screenshot_s3_key: Mapped[str | None] = mapped_column(Text)

    # Extracted structured data
    metadata_extracted: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    competitor = relationship("Competitor", back_populates="snapshots")

    def __repr__(self) -> str:
        return f"<Snapshot {self.url} @ {self.captured_at}>"
