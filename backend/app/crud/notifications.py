"""Notification settings and delivery-record database access."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.notification_setting import Notification, NotificationSetting
from app.models.policy import Policy
from app.models.user import User
from app.models.user_policy import UserPolicyState

SETTING_FIELDS = frozenset(
    {
        "notification_enabled",
        "deadline_d7_enabled",
        "deadline_d3_enabled",
        "deadline_d0_enabled",
        "email_enabled",
        "push_enabled",
    }
)


@dataclass(slots=True)
class DeadlineCandidate:
    """Database projection consumed by the pure scheduling service."""

    user_id: int
    email: str
    policy_id: int
    policy_title: str
    application_end_date: date
    settings: NotificationSetting


def get_notification_setting(
    db: Session,
    user_id: int,
) -> NotificationSetting | None:
    """Return a user's channel and deadline preferences."""

    return db.get(NotificationSetting, user_id)


def get_or_create_notification_setting(
    db: Session,
    user_id: int,
) -> NotificationSetting:
    """Return settings, creating defaults when the account is new."""

    setting = get_notification_setting(db, user_id)
    if setting is None:
        setting = NotificationSetting(user_id=user_id)
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting


def update_notification_setting(
    db: Session,
    *,
    user_id: int,
    values: Mapping[str, object],
) -> NotificationSetting:
    """Patch only supported notification toggles."""

    setting = get_or_create_notification_setting(db, user_id)
    for field, value in values.items():
        if field not in SETTING_FIELDS:
            raise ValueError(f"Unsupported notification setting: {field}")
        if not isinstance(value, bool):
            raise ValueError(f"{field} must be boolean")
        setattr(setting, field, value)
    db.commit()
    db.refresh(setting)
    return setting


def list_deadline_candidates(
    db: Session,
    *,
    earliest_date: date,
    latest_date: date,
) -> list[DeadlineCandidate]:
    """Return bookmarked policies that may need a deadline notification."""

    statement = (
        select(User, Policy, NotificationSetting)
        .join(UserPolicyState, UserPolicyState.user_id == User.id)
        .join(Policy, Policy.id == UserPolicyState.policy_id)
        .join(NotificationSetting, NotificationSetting.user_id == User.id)
        .where(
            UserPolicyState.is_bookmarked.is_(True),
            NotificationSetting.notification_enabled.is_(True),
            Policy.is_active.is_(True),
            Policy.is_ongoing.is_(False),
            Policy.application_end_date.is_not(None),
            Policy.application_end_date >= earliest_date,
            Policy.application_end_date <= latest_date,
        )
    )
    return [
        DeadlineCandidate(
            user_id=user.id,
            email=user.email,
            policy_id=policy.id,
            policy_title=policy.title,
            application_end_date=policy.application_end_date,
            settings=settings,
        )
        for user, policy, settings in db.execute(statement).all()
        if policy.application_end_date is not None
    ]


def create_notification_if_new(
    db: Session,
    *,
    user_id: int,
    policy_id: int | None,
    notification_type: str,
    title: str,
    body: str,
    scheduled_at: object,
    deduplication_key: str,
) -> Notification | None:
    """Insert a delivery record once, using the database unique key."""

    notification = Notification(
        user_id=user_id,
        policy_id=policy_id,
        notification_type=notification_type,
        title=title,
        body=body,
        scheduled_at=scheduled_at,
        send_status="PENDING",
        deduplication_key=deduplication_key,
    )
    db.add(notification)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None
    db.refresh(notification)
    return notification


def list_notifications(
    db: Session,
    *,
    user_id: int,
    unread_only: bool = False,
    limit: int = 50,
) -> list[Notification]:
    """Return the user's newest notification records."""

    statement = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        statement = statement.where(Notification.read_at.is_(None))
    statement = statement.order_by(Notification.scheduled_at.desc()).limit(limit)
    return list(db.scalars(statement).all())


def get_notification(
    db: Session,
    *,
    user_id: int,
    notification_id: int,
) -> Notification | None:
    """Return one notification only when owned by the user."""

    statement = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    return db.scalar(statement)


def mark_notification_read(
    db: Session,
    notification: Notification,
    *,
    read_at: object,
) -> Notification:
    """Mark a notification as read."""

    notification.read_at = read_at
    db.commit()
    db.refresh(notification)
    return notification


def mark_notification_sent(
    db: Session,
    notification: Notification,
    *,
    sent_at: object,
    send_status: str,
) -> Notification:
    """Persist a sender result."""

    notification.sent_at = sent_at
    notification.send_status = send_status
    db.commit()
    db.refresh(notification)
    return notification
