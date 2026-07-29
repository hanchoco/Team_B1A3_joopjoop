"""Notification preferences and deduplicated delivery records."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BIGINT_UNSIGNED, DATETIME_FSP6, varchar_enum

if TYPE_CHECKING:
    from app.models.policy import Policy
    from app.models.user import User


class NotificationType(str, Enum):
    """Supported notification events."""

    DEADLINE_D7 = "DEADLINE_D7"
    DEADLINE_D3 = "DEADLINE_D3"
    DEADLINE_D0 = "DEADLINE_D0"
    APPLICATION_STATUS = "APPLICATION_STATUS"
    SYSTEM = "SYSTEM"


class NotificationSendStatus(str, Enum):
    """Delivery lifecycle for a notification record."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class NotificationSetting(Base):
    """Per-user deadline and channel preferences."""

    __tablename__ = "notification_settings"

    user_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    notification_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    deadline_d7_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    deadline_d3_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    deadline_d0_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    email_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    push_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME_FSP6,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="notification_setting")


class Notification(Base):
    """One in-app/delivery notification with a deduplication key."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "read_at"),
        Index("ix_notifications_pending_schedule", "send_status", "scheduled_at"),
    )

    id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_id: Mapped[int | None] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("policies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        varchar_enum(
            NotificationType,
            name="notification_type_enum",
            length=30,
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(
        DATETIME_FSP6,
        nullable=False,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DATETIME_FSP6,
        nullable=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DATETIME_FSP6,
        nullable=True,
    )
    send_status: Mapped[NotificationSendStatus] = mapped_column(
        varchar_enum(
            NotificationSendStatus,
            name="notification_send_status_enum",
            length=20,
        ),
        nullable=False,
        default=NotificationSendStatus.PENDING,
        server_default=NotificationSendStatus.PENDING.value,
    )
    deduplication_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    user: Mapped[User] = relationship(back_populates="notifications")
    policy: Mapped[Policy | None] = relationship(back_populates="notifications")


__all__ = [
    "Notification",
    "NotificationSendStatus",
    "NotificationSetting",
    "NotificationType",
]
