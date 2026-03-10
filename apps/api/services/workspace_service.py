"""Service layer for workspace operations."""

import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from ..models.workspace import Workspace, WorkspaceUsage, WorkspaceUser

logger = logging.getLogger(__name__)

# Plan configuration
PLAN_LIMITS = {
    "starter": {
        "max_competitors": 3,
        "max_briefings_per_month": 4,
        "max_alerts_per_month": 0,
        "max_searches_per_month": 50,
        "max_members": 2,
    },
    "growth": {
        "max_competitors": 10,
        "max_briefings_per_month": 30,
        "max_alerts_per_month": 100,
        "max_searches_per_month": 500,
        "max_members": 10,
    },
    "enterprise": {
        "max_competitors": 50,
        "max_briefings_per_month": -1,  # unlimited
        "max_alerts_per_month": -1,
        "max_searches_per_month": -1,
        "max_members": -1,
    },
}


def _slugify(name: str) -> str:
    """Generate a URL-safe slug from a workspace name."""
    slug = re.sub(r"[^\w\s-]", "", name.lower().strip())
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug[:100]


class WorkspaceService:
    """Handles workspace CRUD and membership operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_workspace(
        self, owner: User, name: str, plan: str = "starter"
    ) -> Workspace:
        """Create a new workspace with the owner as first member."""
        base_slug = _slugify(name)
        slug = base_slug

        # Ensure unique slug
        counter = 1
        while True:
            existing = await self.db.execute(
                select(Workspace).where(Workspace.slug == slug)
            )
            if existing.scalar_one_or_none() is None:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])

        workspace = Workspace(
            name=name,
            slug=slug,
            owner_id=owner.id,
            plan=plan,
        )
        self.db.add(workspace)
        await self.db.flush()

        # Add owner as member
        member = WorkspaceUser(
            workspace_id=workspace.id,
            user_id=owner.id,
            role="owner",
            invite_status="accepted",
        )
        self.db.add(member)

        # Initialize usage tracking
        usage = WorkspaceUsage(
            workspace_id=workspace.id,
            max_competitors=limits["max_competitors"],
            max_briefings_per_month=limits["max_briefings_per_month"],
            max_alerts_per_month=limits["max_alerts_per_month"],
            max_searches_per_month=limits["max_searches_per_month"],
        )
        self.db.add(usage)
        await self.db.flush()
        await self.db.refresh(workspace)

        logger.info("Created workspace %s (%s) for user %s", workspace.id, slug, owner.id)
        return workspace

    async def get_workspace(self, workspace_id: uuid.UUID) -> Workspace | None:
        """Get workspace by ID."""
        result = await self.db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def get_workspace_by_slug(self, slug: str) -> Workspace | None:
        """Get workspace by slug."""
        result = await self.db.execute(
            select(Workspace).where(Workspace.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_user_workspaces(self, user_id: uuid.UUID) -> list[Workspace]:
        """List all workspaces a user is a member of."""
        result = await self.db.execute(
            select(Workspace)
            .join(WorkspaceUser, WorkspaceUser.workspace_id == Workspace.id)
            .where(
                WorkspaceUser.user_id == user_id,
                WorkspaceUser.invite_status == "accepted",
                Workspace.is_active.is_(True),
            )
            .order_by(Workspace.created_at.desc())
        )
        return list(result.scalars().all())

    async def invite_user(
        self,
        workspace_id: uuid.UUID,
        inviter_id: uuid.UUID,
        email: str,
        role: str = "member",
    ) -> WorkspaceUser:
        """Invite a user to a workspace by email."""
        # Check plan limits for member count
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError("Workspace not found")

        limits = PLAN_LIMITS.get(workspace.plan, PLAN_LIMITS["starter"])
        max_members = limits["max_members"]

        if max_members > 0:
            member_count = (
                await self.db.execute(
                    select(func.count()).where(
                        WorkspaceUser.workspace_id == workspace_id
                    )
                )
            ).scalar() or 0
            if member_count >= max_members:
                raise ValueError(
                    f"Member limit reached ({max_members}). Upgrade your plan."
                )

        # Check if user exists
        user_result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = user_result.scalar_one_or_none()

        # Check for existing membership
        if user:
            existing = await self.db.execute(
                select(WorkspaceUser).where(
                    WorkspaceUser.workspace_id == workspace_id,
                    WorkspaceUser.user_id == user.id,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError("User is already a member of this workspace")

        member = WorkspaceUser(
            workspace_id=workspace_id,
            user_id=user.id if user else None,
            role=role,
            invited_email=email,
            invite_status="pending" if not user else "accepted",
        )
        self.db.add(member)
        await self.db.flush()

        logger.info(
            "Invited %s to workspace %s (role=%s)",
            email, workspace_id, role,
        )
        return member

    async def list_workspace_members(
        self, workspace_id: uuid.UUID
    ) -> list[WorkspaceUser]:
        """List all members of a workspace."""
        result = await self.db.execute(
            select(WorkspaceUser)
            .where(WorkspaceUser.workspace_id == workspace_id)
            .order_by(WorkspaceUser.created_at)
        )
        return list(result.scalars().all())

    async def remove_member(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Remove a user from a workspace."""
        result = await self.db.execute(
            select(WorkspaceUser).where(
                WorkspaceUser.workspace_id == workspace_id,
                WorkspaceUser.user_id == user_id,
                WorkspaceUser.role != "owner",  # Cannot remove owner
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            return False
        await self.db.delete(member)
        await self.db.flush()
        logger.info("Removed user %s from workspace %s", user_id, workspace_id)
        return True

    async def update_member_role(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID, role: str
    ) -> WorkspaceUser | None:
        """Update a member's role in a workspace."""
        result = await self.db.execute(
            select(WorkspaceUser).where(
                WorkspaceUser.workspace_id == workspace_id,
                WorkspaceUser.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            return None
        member.role = role
        await self.db.flush()
        return member

    async def check_membership(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceUser | None:
        """Check if a user is a member of a workspace."""
        result = await self.db.execute(
            select(WorkspaceUser).where(
                WorkspaceUser.workspace_id == workspace_id,
                WorkspaceUser.user_id == user_id,
                WorkspaceUser.invite_status == "accepted",
            )
        )
        return result.scalar_one_or_none()

    async def get_usage(self, workspace_id: uuid.UUID) -> WorkspaceUsage | None:
        """Get workspace usage stats."""
        result = await self.db.execute(
            select(WorkspaceUsage).where(
                WorkspaceUsage.workspace_id == workspace_id
            )
        )
        return result.scalar_one_or_none()

    async def check_quota(
        self, workspace_id: uuid.UUID, resource: str
    ) -> tuple[bool, str]:
        """Check if a workspace has quota remaining for a resource.

        Returns (allowed, message).
        """
        usage = await self.get_usage(workspace_id)
        if not usage:
            return False, "Workspace usage record not found"

        checks = {
            "competitors": (usage.competitors_count, usage.max_competitors),
            "briefings": (usage.briefings_generated, usage.max_briefings_per_month),
            "alerts": (usage.alerts_sent, usage.max_alerts_per_month),
            "searches": (usage.searches_performed, usage.max_searches_per_month),
        }

        if resource not in checks:
            return True, "OK"

        current, limit = checks[resource]
        if limit < 0:  # unlimited
            return True, "OK"
        if current >= limit:
            return False, f"{resource.capitalize()} limit reached ({limit}). Upgrade your plan."

        return True, "OK"

    async def increment_usage(
        self, workspace_id: uuid.UUID, resource: str, amount: int = 1
    ) -> None:
        """Increment a usage counter for a workspace."""
        usage = await self.get_usage(workspace_id)
        if not usage:
            return

        field_map = {
            "competitors": "competitors_count",
            "briefings": "briefings_generated",
            "alerts": "alerts_sent",
            "searches": "searches_performed",
            "api_calls": "api_calls",
        }

        field = field_map.get(resource)
        if field:
            setattr(usage, field, getattr(usage, field) + amount)
            await self.db.flush()
