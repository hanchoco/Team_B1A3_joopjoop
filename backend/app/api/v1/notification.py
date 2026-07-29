"""Notification settings and in-app feed routes."""

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.notification import NotificationResponse
from app.schemas.user import NotificationSettingResponse, NotificationSettingUpdate
from app.services import notification_service

router = APIRouter(tags=["notifications"])


@router.get(
    "/users/me/notification-settings",
    response_model=NotificationSettingResponse,
)
def get_notification_settings(
    db: DbSession,
    current_user: CurrentUser,
) -> NotificationSettingResponse:
    """Return all, deadline, email, and push toggles."""

    setting = notification_service.get_settings(db, current_user.id)
    return NotificationSettingResponse.model_validate(setting)


@router.patch(
    "/users/me/notification-settings",
    response_model=NotificationSettingResponse,
)
def patch_notification_settings(
    payload: NotificationSettingUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> NotificationSettingResponse:
    """Patch notification preferences."""

    setting = notification_service.update_settings(
        db,
        user_id=current_user.id,
        values=payload.model_dump(exclude_unset=True),
    )
    return NotificationSettingResponse.model_validate(setting)


@router.get(
    "/users/me/notifications",
    response_model=list[NotificationResponse],
)
def list_notifications(
    db: DbSession,
    current_user: CurrentUser,
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[NotificationResponse]:
    """Return the newest in-app notification records."""

    records = notification_service.list_feed(
        db,
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
    )
    return [NotificationResponse.model_validate(record) for record in records]


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_notification_read(
    notification_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> NotificationResponse:
    """Mark one owned notification as read."""

    notification = notification_service.mark_read(
        db,
        user_id=current_user.id,
        notification_id=notification_id,
    )
    return NotificationResponse.model_validate(notification)
