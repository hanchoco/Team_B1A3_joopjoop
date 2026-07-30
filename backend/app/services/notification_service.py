"""Notification preference, scheduling, and feed orchestration."""

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.crud import notifications as notification_crud
from app.db.session import SessionLocal
from app.models.notification_setting import Notification, NotificationSetting
from app.services.errors import NotFoundError
from app.services.notification.email_adapter import get_email_adapter
from app.services.notification.scheduler import (
    KST,
    InterestedPolicyRecord,
    NotificationPreferences,
    build_notification_events,
)
from app.services.notification.sender import NotificationDispatcher, NotificationRecipient


def get_settings(db: Session, user_id: int) -> NotificationSetting:
    """Return settings with product defaults for a new user."""

    return notification_crud.get_or_create_notification_setting(db, user_id)


def update_settings(
    db: Session,
    *,
    user_id: int,
    values: Mapping[str, object],
) -> NotificationSetting:
    """Apply all/channel/deadline toggles."""

    return notification_crud.update_notification_setting(
        db,
        user_id=user_id,
        values=values,
    )


def create_due_deadline_notifications(
    db: Session,
    *,
    as_of: datetime | None = None,
) -> list[Notification]:
    """Create deduplicated D-7, D-3, and D-day feed records."""

    if as_of is None:
        current = datetime.now(KST)
    elif as_of.tzinfo is None:
        current = as_of.replace(tzinfo=KST)
    else:
        current = as_of.astimezone(KST)
    candidates = notification_crud.list_deadline_candidates(
        db,
        earliest_date=current.date(),
        latest_date=current.date() + timedelta(days=7),
    )
    preferences_by_key = {
        (candidate.user_id, candidate.policy_id): NotificationPreferences(
            all_enabled=candidate.settings.notification_enabled,
            d7_enabled=candidate.settings.deadline_d7_enabled,
            d3_enabled=candidate.settings.deadline_d3_enabled,
            d0_enabled=candidate.settings.deadline_d0_enabled,
            email_enabled=candidate.settings.email_enabled,
            push_enabled=candidate.settings.push_enabled,
        )
        for candidate in candidates
    }
    candidate_by_key = {
        (candidate.user_id, candidate.policy_id): candidate for candidate in candidates
    }
    scheduler_records = [
        InterestedPolicyRecord(
            user_id=candidate.user_id,
            policy_id=candidate.policy_id,
            policy_title=candidate.policy_title,
            application_end_date=candidate.application_end_date,
            is_bookmarked=True,
            preferences=preferences_by_key[(candidate.user_id, candidate.policy_id)],
        )
        for candidate in candidates
    ]
    dispatcher = NotificationDispatcher(email_adapter=get_email_adapter(), push_adapter=None)
    created: list[Notification] = []
    for event in build_notification_events(scheduler_records, as_of=current):
        notification = notification_crud.create_notification_if_new(
            db,
            user_id=event.user_id,
            policy_id=event.policy_id,
            notification_type=event.type,
            title=event.title,
            body=event.body,
            scheduled_at=event.scheduled_at.replace(tzinfo=None),
            deduplication_key=event.dedup_key,
        )
        if notification is None:
            continue
        created.append(notification)

        key = (event.user_id, event.policy_id)
        candidate = candidate_by_key[key]
        preferences = preferences_by_key[key]
        recipient = NotificationRecipient(
            user_id=event.user_id,
            email=candidate.email,
            push_token=None,
        )
        result = asyncio.run(dispatcher.dispatch(event, recipient, preferences))

        send_status: str | None = None
        if result.sent_count > 0:
            send_status = "SENT"
        elif any(attempt.status == "failed" for attempt in result.attempts):
            send_status = "FAILED"
        if send_status is not None:
            notification_crud.mark_notification_sent(
                db,
                notification,
                sent_at=datetime.now(UTC).replace(tzinfo=None),
                send_status=send_status,
            )
    return created


def list_feed(
    db: Session,
    *,
    user_id: int,
    unread_only: bool,
    limit: int,
) -> list[Notification]:
    """Return the in-app notification feed."""

    return notification_crud.list_notifications(
        db,
        user_id=user_id,
        unread_only=unread_only,
        limit=limit,
    )


def mark_read(
    db: Session,
    *,
    user_id: int,
    notification_id: int,
) -> Notification:
    """Mark one owned notification as read."""

    notification = notification_crud.get_notification(
        db,
        user_id=user_id,
        notification_id=notification_id,
    )
    if notification is None:
        raise NotFoundError("알림을 찾을 수 없습니다.")
    return notification_crud.mark_notification_read(
        db,
        notification,
        read_at=datetime.now(UTC).replace(tzinfo=None),
    )


def run_scheduled_deadline_notification_job() -> list[Notification]:
    """APScheduler cron 잡 진입점 — 요청 스코프 세션이 없어 직접 세션을 연다."""

    db = SessionLocal()
    try:
        return create_due_deadline_notifications(db)
    finally:
        db.close()
