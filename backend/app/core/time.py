"""Service-local date and time helpers."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def today_in_kst(now: datetime | None = None) -> date:
    """Return the current calendar date in the service's KST timezone."""

    current = now or datetime.now(KST)
    if current.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return current.astimezone(KST).date()
