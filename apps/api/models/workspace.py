"""Workspace ORM models for multi-tenant team support."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Plan & billing
    plan: Mapped[str] = mapped_column(
        String(50), default="starter"
    )  # starter | growth | enterprise
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255))

    # Settings
    logo_url: Mapped[str | None] = mapped_column(Text)
    settings: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship(
        "WorkspaceUser", back_populates="workspace", cascade="all, delete-orphan"
    )
    usage = relationship(
        "WorkspaceUsage", back_populates="workspace", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Workspace {self.name} ({self.slug})>"


class WorkspaceUser(Base):
    __tablename__ = "workspace_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(50), default="member"
    )  # owner | admin | member | viewer
    invited_email: Mapped[str | None] = mapped_column(String(320))
    invite_status: Mapped[str] = mapped_column(
        String(20), default="accepted"
    )  # pending | accepted | declined

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<WorkspaceUser workspace={self.workspace_id} user={self.user_id} role={self.role}>"


class WorkspaceUsage(Base):
    __tablename__ = "workspace_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Usage counters
    competitors_count: Mapped[int] = mapped_column(Integer, default=0)
    briefings_generated: Mapped[int] = mapped_column(Integer, default=0)
    alerts_sent: Mapped[int] = mapped_column(Integer, default=0)
    searches_performed: Mapped[int] = mapped_column(Integer, default=0)
    api_calls: Mapped[int] = mapped_column(Integer, default=0)

    # Plan limits
    max_competitors: Mapped[int] = mapped_column(Integer, default=3)
    max_briefings_per_month: Mapped[int] = mapped_column(Integer, default=4)
    max_alerts_per_month: Mapped[int] = mapped_column(Integer, default=0)
    max_searches_per_month: Mapped[int] = mapped_column(Integer, default=50)

    # Period tracking
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    workspace = relationship("Workspace", back_populates="usage")

    def __repr__(self) -> str:
        return f"<WorkspaceUsage workspace={self.workspace_id}>"
