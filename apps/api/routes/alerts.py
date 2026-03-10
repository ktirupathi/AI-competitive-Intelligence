"""Alert routes: list, read, and manage alerts."""

import uuid

from fastapi import APIRouter, HTTPException, Query, status

from ..deps import CurrentUser, DbSession
from ..schemas.alert import AlertListResponse, AlertMarkRead, AlertRead
from ..services.alert_service import AlertService

router = APIRouter()


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    db: DbSession,
    user: CurrentUser,
    workspace_id: uuid.UUID = Query(...),
    severity: str | None = Query(None),
    alert_type: str | None = Query(None),
    is_read: bool | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> AlertListResponse:
    """List alerts for a workspace."""
    from ..services.workspace_service import WorkspaceService

    ws_service = WorkspaceService(db)
    member = await ws_service.check_membership(workspace_id, user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )

    service = AlertService(db)
    items, total = await service.list_alerts(
        workspace_id=workspace_id,
        severity=severity,
        alert_type=alert_type,
        is_read=is_read,
        offset=offset,
        limit=limit,
    )
    return AlertListResponse(
        items=[AlertRead.model_validate(a) for a in items],
        total=total,
    )


@router.post("/mark-read", status_code=status.HTTP_200_OK)
async def mark_alerts_read(
    data: AlertMarkRead,
    db: DbSession,
    user: CurrentUser,
    workspace_id: uuid.UUID = Query(...),
) -> dict[str, int]:
    """Mark alerts as read."""
    from ..services.workspace_service import WorkspaceService

    ws_service = WorkspaceService(db)
    member = await ws_service.check_membership(workspace_id, user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )

    service = AlertService(db)
    updated = await service.mark_read(data.alert_ids, workspace_id)
    await db.commit()
    return {"updated": updated}
