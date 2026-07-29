"""Deadline notification scheduling and adapter-based delivery."""

from .scheduler import (
    DEADLINE_OFFSETS,
    InterestedPolicyRecord,
    NotificationEvent,
    NotificationPreferences,
    build_notification_events,
    schedule_notifications,
)
from .sender import (
    DeliveryAttempt,
    DeliveryResult,
    EmailAdapter,
    NotificationDispatcher,
    NotificationRecipient,
    PushAdapter,
    send_notification,
)

__all__ = [
    "DEADLINE_OFFSETS",
    "DeliveryAttempt",
    "DeliveryResult",
    "EmailAdapter",
    "InterestedPolicyRecord",
    "NotificationDispatcher",
    "NotificationEvent",
    "NotificationPreferences",
    "NotificationRecipient",
    "PushAdapter",
    "build_notification_events",
    "schedule_notifications",
    "send_notification",
]
