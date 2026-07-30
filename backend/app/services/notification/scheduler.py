"""Pure deadline-notification scheduling.

The scheduler receives records already loaded by the CRUD layer. It performs no
database queries and only emits the three product-defined triggers: D-7, D-3,
and deadline day.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
DEADLINE_OFFSETS = (7, 3, 0)
_EVENT_TYPES = {
    7: "DEADLINE_D7",
    3: "DEADLINE_D3",
    0: "DEADLINE_D0",
}


@dataclass(frozen=True, slots=True)
class NotificationPreferences:
    """User settings used by both scheduling and delivery."""

    all_enabled: bool = True
    d7_enabled: bool = True
    d3_enabled: bool = True
    d0_enabled: bool = True
    email_enabled: bool = True
    push_enabled: bool = True

    def deadline_enabled(self, days_left: int) -> bool:
        if days_left == 7:
            return self.d7_enabled
        if days_left == 3:
            return self.d3_enabled
        if days_left == 0:
            return self.d0_enabled
        return False


@dataclass(frozen=True, slots=True)
class InterestedPolicyRecord:
    """Database-independent projection consumed by the scheduler."""

    user_id: int
    policy_id: int
    policy_title: str
    application_end_date: date
    is_bookmarked: bool
    preferences: NotificationPreferences


@dataclass(frozen=True, slots=True)
class NotificationEvent:
    """One deduplicatable deadline event."""

    user_id: int
    policy_id: int
    type: str
    title: str
    body: str
    scheduled_at: datetime
    dedup_key: str
    email_enabled: bool
    push_enabled: bool

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["scheduled_at"] = self.scheduled_at.isoformat()
        return payload

    def to_persistence_dict(self) -> dict[str, object]:
        """Return field names accepted by ``crud.notifications``."""

        return {
            "user_id": self.user_id,
            "policy_id": self.policy_id,
            "notification_type": self.type,
            "title": self.title,
            "body": self.body,
            "scheduled_at": self.scheduled_at,
            "deduplication_key": self.dedup_key,
        }


def _parse_date(value: object, *, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an ISO date") from exc
    raise ValueError(f"{field_name} must be a date")


def _required_text(
    record: Mapping[str, object],
    *keys: str,
) -> str:
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    raise ValueError(f"one of {keys!r} is required")


def _required_id(record: Mapping[str, object], key: str) -> int:
    value = record.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{key} must be a positive integer")
    return value


def _bool_setting(
    settings: Mapping[str, object],
    keys: tuple[str, ...],
    *,
    default: bool,
) -> bool:
    for key in keys:
        if key not in settings:
            continue
        value = settings[key]
        if not isinstance(value, bool):
            raise ValueError(f"notification setting {key} must be boolean")
        return value
    return default


def preferences_from_mapping(
    settings: Mapping[str, object],
) -> NotificationPreferences:
    """Build strict settings from common DB/API projection names."""

    return NotificationPreferences(
        all_enabled=_bool_setting(
            settings,
            ("all_enabled", "notification_enabled", "is_enabled"),
            default=True,
        ),
        d7_enabled=_bool_setting(
            settings,
            ("d7_enabled", "deadline_d7_enabled", "deadline_7_enabled"),
            default=True,
        ),
        d3_enabled=_bool_setting(
            settings,
            ("d3_enabled", "deadline_d3_enabled", "deadline_3_enabled"),
            default=True,
        ),
        d0_enabled=_bool_setting(
            settings,
            (
                "d0_enabled",
                "deadline_d0_enabled",
                "deadline_day_enabled",
            ),
            default=True,
        ),
        email_enabled=_bool_setting(
            settings,
            ("email_enabled",),
            default=True,
        ),
        push_enabled=_bool_setting(
            settings,
            ("push_enabled",),
            default=True,
        ),
    )


def record_from_mapping(
    record: Mapping[str, object],
) -> InterestedPolicyRecord:
    """Convert a CRUD projection to a scheduler input record."""

    raw_settings = record.get("notification_setting", record.get("settings", {}))
    if isinstance(raw_settings, NotificationPreferences):
        preferences = raw_settings
    elif isinstance(raw_settings, Mapping):
        preferences = preferences_from_mapping(raw_settings)
    else:
        raise ValueError("notification_setting must be an object")
    is_bookmarked = record.get("is_bookmarked")
    if not isinstance(is_bookmarked, bool):
        raise ValueError("is_bookmarked must be boolean")
    raw_end_date = record.get(
        "application_end_date",
        record.get("policy_end_date"),
    )
    return InterestedPolicyRecord(
        user_id=_required_id(record, "user_id"),
        policy_id=_required_id(record, "policy_id"),
        policy_title=_required_text(record, "policy_title", "title"),
        application_end_date=_parse_date(
            raw_end_date,
            field_name="application_end_date",
        ),
        is_bookmarked=is_bookmarked,
        preferences=preferences,
    )


def _dedup_key(record: InterestedPolicyRecord, event_type: str) -> str:
    identity = "|".join(
        (
            str(record.user_id),
            str(record.policy_id),
            event_type,
            record.application_end_date.isoformat(),
        )
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return f"policy-deadline:{digest}"


def _message(
    policy_title: str,
    *,
    days_left: int,
) -> tuple[str, str]:
    if days_left == 0:
        title = f"[마감일] {policy_title}"
        body = f"관심 정책 '{policy_title}'의 신청 마감일입니다."
    else:
        title = f"[D-{days_left}] {policy_title}"
        body = f"관심 정책 '{policy_title}'의 신청 마감까지 " f"{days_left}일 남았습니다."
    return title, body


def build_notification_events(
    records: Iterable[InterestedPolicyRecord | Mapping[str, object]],
    *,
    as_of: datetime | None = None,
) -> list[NotificationEvent]:
    """Emit today's fixed deadline events and remove duplicate keys."""

    if as_of is None:
        current = datetime.now(KST)
    elif as_of.tzinfo is None:
        current = as_of.replace(tzinfo=KST)
    else:
        current = as_of.astimezone(KST)

    # "한국시간 오전 9시"를 의미하는 naive 값. 이 프로젝트의 다른 타임스탬프(created_at 등)는
    # naive UTC 관례를 쓰지만, 이 필드만 의도적으로 naive KST다.
    scheduled_at = datetime.combine(current.date(), time(hour=9))
    events: list[NotificationEvent] = []
    seen_keys: set[str] = set()
    for item in records:
        record = item if isinstance(item, InterestedPolicyRecord) else record_from_mapping(item)
        if record.is_bookmarked is not True:
            continue
        preferences = record.preferences
        if not preferences.all_enabled:
            continue
        if not preferences.email_enabled and not preferences.push_enabled:
            continue
        days_left = (record.application_end_date - current.date()).days
        if days_left not in DEADLINE_OFFSETS:
            continue
        if not preferences.deadline_enabled(days_left):
            continue
        event_type = _EVENT_TYPES[days_left]
        dedup_key = _dedup_key(record, event_type)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        title, body = _message(record.policy_title, days_left=days_left)
        events.append(
            NotificationEvent(
                user_id=record.user_id,
                policy_id=record.policy_id,
                type=event_type,
                title=title,
                body=body,
                scheduled_at=scheduled_at,
                dedup_key=dedup_key,
                email_enabled=preferences.email_enabled,
                push_enabled=preferences.push_enabled,
            )
        )
    return events


def schedule_notifications(
    records: Iterable[InterestedPolicyRecord | Mapping[str, object]],
    *,
    as_of: datetime | None = None,
) -> list[NotificationEvent]:
    """Compatibility-named entry point for periodic scheduler jobs."""

    return build_notification_events(records, as_of=as_of)
