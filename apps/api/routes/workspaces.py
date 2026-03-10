"""Workspace routes: CRUD, membership, and usage."""

import uuid

from fastapi import APIRouter, HTTPException, Query, status

from ..deps import CurrentUser, DbSession
from ..schemas.workspace import (
    MemberRoleUpdate,
    WorkspaceCreate,
    WorkspaceInvite,
    WorkspaceListResponse,
    WorkspaceMemberRead,
    WorkspaceRead,
    WorkspaceUsageRead,
)
from ..services.audit_log_service import log_action
from ..services.workspace_service import WorkspaceService

router = APIRouter()


@router.get("", response_model=WorkspaceListResponse)
async def list_workspaces(
    db: DbSession,
    user: CurrentUser,
) -> WorkspaceListResponse:
    """List all workspaces the current user belongs to."""
    service = WorkspaceService(db)
    workspaces = await service.list_user_workspaces(user.id)
    return WorkspaceListResponse(
        items=[WorkspaceRead.model_validate(w) for w in workspaces]
    )


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: WorkspaceCreate,
    db: DbSession,
    user: CurrentUser,
) -> WorkspaceRead:
    """Create a new workspace."""
    service = WorkspaceService(db)
    workspace = await service.create_workspace(
        owner=user, name=data.name, plan=data.plan
    )
    await log_action(
        db,
        action="create",
        resource="workspace",
        user_id=user.id,
        workspace_id=workspace.id,
        resource_id=str(workspace.id),
    )
    await db.commit()
    return WorkspaceRead.model_validate(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(
    workspace_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> WorkspaceRead:
    """Get workspace details."""
    service = WorkspaceService(db)
    member = await service.check_membership(workspace_id, user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    workspace = await service.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return WorkspaceRead.model_validate(workspace)


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberRead])
async def list_members(
    workspace_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> list[WorkspaceMemberRead]:
    """List all members of a workspace."""
    service = WorkspaceService(db)
    member = await service.check_membership(workspace_id, user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    members = await service.list_workspace_members(workspace_id)
    return [WorkspaceMemberRead.model_validate(m) for m in members]


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberRead,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    workspace_id: uuid.UUID,
    data: WorkspaceInvite,
    db: DbSession,
    user: CurrentUser,
) -> WorkspaceMemberRead:
    """Invite a user to a workspace."""
    service = WorkspaceService(db)
    member = await service.check_membership(workspace_id, user.id)
    if not member or member.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can invite members",
        )
    try:
        new_member = await service.invite_user(
            workspace_id=workspace_id,
            inviter_id=user.id,
            email=data.email,
            role=data.role,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    await log_action(
        db,
        action="invite_member",
        resource="workspace",
        user_id=user.id,
        workspace_id=workspace_id,
        metadata={"invited_email": data.email, "role": data.role},
    )
    await db.commit()
    return WorkspaceMemberRead.model_validate(new_member)


@router.patch(
    "/{workspace_id}/members/{member_user_id}",
    response_model=WorkspaceMemberRead,
)
async def update_member_role(
    workspace_id: uuid.UUID,
    member_user_id: uuid.UUID,
    data: MemberRoleUpdate,
    db: DbSession,
    user: CurrentUser,
) -> WorkspaceMemberRead:
    """Update a member's role."""
    service = WorkspaceService(db)
    requester = await service.check_membership(workspace_id, user.id)
    if not requester or requester.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can change roles",
        )
    updated = await service.update_member_role(workspace_id, member_user_id, data.role)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )
    await db.commit()
    return WorkspaceMemberRead.model_validate(updated)


@router.delete(
    "/{workspace_id}/members/{member_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    workspace_id: uuid.UUID,
    member_user_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> None:
    """Remove a member from a workspace."""
    service = WorkspaceService(db)
    requester = await service.check_membership(workspace_id, user.id)
    if not requester or requester.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can remove members",
        )
    removed = await service.remove_member(workspace_id, member_user_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found or cannot remove owner",
        )
    await log_action(
        db,
        action="remove_member",
        resource="workspace",
        user_id=user.id,
        workspace_id=workspace_id,
        metadata={"removed_user_id": str(member_user_id)},
    )
    await db.commit()


@router.get("/{workspace_id}/usage", response_model=WorkspaceUsageRead)
async def get_usage(
    workspace_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> WorkspaceUsageRead:
    """Get workspace usage statistics."""
    service = WorkspaceService(db)
    member = await service.check_membership(workspace_id, user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    usage = await service.get_usage(workspace_id)
    if not usage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usage data not found",
        )
    return WorkspaceUsageRead.model_validate(usage)
