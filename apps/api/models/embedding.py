"""Vector embedding ORM model for semantic search via pgvector."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Polymorphic reference: which table and row this embedding belongs to
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # snapshot | news_item | job_posting | review | social_post | insight
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    content_text: Mapped[str | None] = mapped_column(Text)
    embedding = mapped_column(Vector(1536), nullable=False)

    model: Mapped[str] = mapped_column(
        String(100), default="text-embedding-3-small"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Embedding {self.source_type}:{self.source_id}>"
