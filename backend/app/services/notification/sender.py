"""Notification delivery orchestration with pluggable channel adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from .scheduler import NotificationEvent, NotificationPreferences

DeliveryChannel = Literal["email", "push"]
DeliveryStatus = Literal["sent", "skipped", "failed"]


class EmailAdapter(Protocol):
    """Adapter contract implemented by an email provider integration."""

    async def send_email(
        self,
        *,
        recipient: str,
        title: str,
        body: str,
        dedup_key: str,
    ) -> None:
        """Send one idempotent email."""


class PushAdapter(Protocol):
    """Adapter contract implemented by a push provider integration."""

    async def send_push(
        self,
        *,
        device_token: str,
        title: str,
        body: str,
        dedup_key: str,
    ) -> None:
        """Send one idempotent push message."""


@dataclass(frozen=True, slots=True)
class NotificationRecipient:
    """Delivery addresses already loaded by a CRUD layer."""

    user_id: int
    email: str | None = None
    push_token: str | None = None


@dataclass(frozen=True, slots=True)
class DeliveryAttempt:
    """Per-channel delivery outcome without provider-sensitive details."""

    channel: DeliveryChannel
    status: DeliveryStatus
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """Aggregate result for one scheduled event."""

    dedup_key: str
    attempts: tuple[DeliveryAttempt, ...]

    @property
    def sent_count(self) -> int:
        return sum(attempt.status == "sent" for attempt in self.attempts)


def _deadline_toggle_enabled(
    event: NotificationEvent,
    preferences: NotificationPreferences,
) -> bool:
    days_by_type = {
        "DEADLINE_D7": 7,
        "DEADLINE_D3": 3,
        "DEADLINE_D0": 0,
    }
    days_left = days_by_type.get(event.type)
    return days_left is not None and preferences.deadline_enabled(days_left)


class NotificationDispatcher:
    """Deliver an event only through enabled and configured adapters."""

    def __init__(
        self,
        *,
        email_adapter: EmailAdapter | None = None,
        push_adapter: PushAdapter | None = None,
    ) -> None:
        self._email_adapter = email_adapter
        self._push_adapter = push_adapter

    async def dispatch(
        self,
        event: NotificationEvent,
        recipient: NotificationRecipient,
        preferences: NotificationPreferences,
    ) -> DeliveryResult:
        """Dispatch without querying or mutating notification settings."""

        if event.user_id != recipient.user_id:
            raise ValueError("event and recipient user_id must match")
        if not preferences.all_enabled:
            return DeliveryResult(
                dedup_key=event.dedup_key,
                attempts=(
                    DeliveryAttempt("email", "skipped", "all_disabled"),
                    DeliveryAttempt("push", "skipped", "all_disabled"),
                ),
            )
        if not _deadline_toggle_enabled(event, preferences):
            return DeliveryResult(
                dedup_key=event.dedup_key,
                attempts=(
                    DeliveryAttempt("email", "skipped", "deadline_disabled"),
                    DeliveryAttempt("push", "skipped", "deadline_disabled"),
                ),
            )

        email_attempt = await self._send_email(event, recipient, preferences)
        push_attempt = await self._send_push(event, recipient, preferences)
        return DeliveryResult(
            dedup_key=event.dedup_key,
            attempts=(email_attempt, push_attempt),
        )

    async def _send_email(
        self,
        event: NotificationEvent,
        recipient: NotificationRecipient,
        preferences: NotificationPreferences,
    ) -> DeliveryAttempt:
        if not event.email_enabled or not preferences.email_enabled:
            return DeliveryAttempt("email", "skipped", "channel_disabled")
        if not recipient.email:
            return DeliveryAttempt("email", "skipped", "missing_recipient")
        if self._email_adapter is None:
            return DeliveryAttempt("email", "skipped", "adapter_unavailable")
        try:
            await self._email_adapter.send_email(
                recipient=recipient.email,
                title=event.title,
                body=event.body,
                dedup_key=f"{event.dedup_key}:email",
            )
        except Exception as exc:  # Provider errors are isolated per channel.
            return DeliveryAttempt("email", "failed", type(exc).__name__)
        return DeliveryAttempt("email", "sent")

    async def _send_push(
        self,
        event: NotificationEvent,
        recipient: NotificationRecipient,
        preferences: NotificationPreferences,
    ) -> DeliveryAttempt:
        if not event.push_enabled or not preferences.push_enabled:
            return DeliveryAttempt("push", "skipped", "channel_disabled")
        if not recipient.push_token:
            return DeliveryAttempt("push", "skipped", "missing_recipient")
        if self._push_adapter is None:
            return DeliveryAttempt("push", "skipped", "adapter_unavailable")
        try:
            await self._push_adapter.send_push(
                device_token=recipient.push_token,
                title=event.title,
                body=event.body,
                dedup_key=f"{event.dedup_key}:push",
            )
        except Exception as exc:  # Provider errors are isolated per channel.
            return DeliveryAttempt("push", "failed", type(exc).__name__)
        return DeliveryAttempt("push", "sent")


async def send_notification(
    event: NotificationEvent,
    recipient: NotificationRecipient,
    preferences: NotificationPreferences,
    *,
    email_adapter: EmailAdapter | None = None,
    push_adapter: PushAdapter | None = None,
) -> DeliveryResult:
    """Functional entry point for jobs that do not keep a dispatcher instance."""

    dispatcher = NotificationDispatcher(
        email_adapter=email_adapter,
        push_adapter=push_adapter,
    )
    return await dispatcher.dispatch(event, recipient, preferences)
