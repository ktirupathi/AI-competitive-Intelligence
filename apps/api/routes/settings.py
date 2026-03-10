"""User settings routes."""

from fastapi import APIRouter, status

from ..deps import CurrentUser, DbSession
from ..schemas.settings import (
    NotificationPrefsUpdate,
    UserSettingsRead,
    UserSettingsUpdate,
)

router = APIRouter()


@router.get("", response_model=UserSettingsRead)
async def get_settings(
    user: CurrentUser,
) -> UserSettingsRead:
    """Get the current user's settings."""
    return UserSettingsRead.model_validate(user)


@router.patch("", response_model=UserSettingsRead)
async def update_settings(
    data: UserSettingsUpdate,
    db: DbSession,
    user: CurrentUser,
) -> UserSettingsRead:
    """Update the current user's profile settings."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    await db.commit()
    return UserSettingsRead.model_validate(user)


@router.patch("/notifications", response_model=UserSettingsRead)
async def update_notification_preferences(
    data: NotificationPrefsUpdate,
    db: DbSession,
    user: CurrentUser,
) -> UserSettingsRead:
    """Update notification preferences."""
    current_prefs = user.notification_prefs or {}
    new_prefs = data.model_dump(exclude_unset=True)
    current_prefs.update(new_prefs)
    user.notification_prefs = current_prefs

    await db.flush()
    await db.refresh(user)
    await db.commit()
    return UserSettingsRead.model_validate(user)


@router.delete("/account", status_code=status.HTTP_200_OK)
async def deactivate_account(
    db: DbSession,
    user: CurrentUser,
) -> dict[str, str]:
    """Deactivate the current user's account.

    This soft-deletes the user. Data is retained for 30 days
    before permanent deletion.
    """
    user.is_active = False
    await db.flush()
    await db.commit()
    return {"status": "deactivated", "message": "Account has been deactivated."}
