"""Notification feed schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    """A persisted in-app notification."""

    id: int
    policy_id: int | None
    notification_type: str
    title: str
    body: str
    scheduled_at: datetime
    sent_at: datetime | None
    read_at: datetime | None
    send_status: str

    model_config = ConfigDict(from_attributes=True)
