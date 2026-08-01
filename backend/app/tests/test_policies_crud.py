"""Unit coverage for read-only helpers in app.crud.policies."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.core.time import today_in_kst
from app.crud.policies import list_external_ids, list_policies
from app.db.session import SessionLocal
from app.models.policy import Policy


def _policy(source: str, external_id: str, title: str) -> Policy:
    return Policy(
        source=source,
        external_id=external_id,
        title=title,
        application_start_date=date(2026, 1, 1),
        application_end_date=date(2026, 12, 31),
        is_ongoing=False,
        status="ACTIVE",
        is_active=True,
    )


def test_list_external_ids_scopes_to_one_source() -> None:
    with SessionLocal() as db:
        db.add_all(
            [
                _policy("ONTONG_YOUTH", "ext-1", "정책 1"),
                _policy("ONTONG_YOUTH", "ext-2", "정책 2"),
                _policy("MANUAL", "ext-3", "정책 3"),
            ]
        )
        db.commit()

        result = list_external_ids(db, source="ONTONG_YOUTH")

    assert result == {"ext-1", "ext-2"}


def test_list_external_ids_returns_empty_set_when_no_matches() -> None:
    with SessionLocal() as db:
        result = list_external_ids(db, source="ONTONG_YOUTH")

    assert result == set()


def test_today_in_kst_uses_korean_calendar_date() -> None:
    utc_instant = datetime(2026, 7, 31, 15, tzinfo=UTC)

    assert today_in_kst(utc_instant) == date(2026, 8, 1)


def test_deadline_sort_excludes_expired_and_closed_policies() -> None:
    as_of = date(2026, 8, 1)

    def deadline_policy(
        external_id: str,
        *,
        end_date: date | None,
        status: str = "ACTIVE",
        is_ongoing: bool = False,
    ) -> Policy:
        return Policy(
            source="MANUAL",
            external_id=external_id,
            title=external_id,
            application_start_date=as_of - timedelta(days=30),
            application_end_date=end_date,
            is_ongoing=is_ongoing,
            published_date=as_of,
            status=status,
            is_active=True,
        )

    with SessionLocal() as db:
        db.add_all(
            [
                deadline_policy("expired", end_date=as_of - timedelta(days=1)),
                deadline_policy(
                    "expired-ongoing-flag",
                    end_date=as_of - timedelta(days=1),
                    is_ongoing=True,
                ),
                deadline_policy("due-today", end_date=as_of),
                deadline_policy("due-soon", end_date=as_of + timedelta(days=2)),
                deadline_policy("due-later", end_date=as_of + timedelta(days=10)),
                deadline_policy(
                    "closed-with-future-date",
                    end_date=as_of + timedelta(days=1),
                    status="CLOSED",
                ),
                deadline_policy(
                    "archived-with-future-date",
                    end_date=as_of + timedelta(days=1),
                    status="ARCHIVED",
                ),
                deadline_policy("open-ended", end_date=None, is_ongoing=True),
            ]
        )
        db.commit()

        policies, total = list_policies(
            db,
            sort="deadline",
            deadline_as_of=as_of,
        )

        latest_policies, latest_total = list_policies(db, sort="latest")

    assert [policy.external_id for policy in policies] == [
        "due-today",
        "due-soon",
        "due-later",
        "open-ended",
    ]
    assert total == 4
    assert {policy.external_id for policy in latest_policies} == {
        "expired",
        "expired-ongoing-flag",
        "due-today",
        "due-soon",
        "due-later",
        "closed-with-future-date",
        "archived-with-future-date",
        "open-ended",
    }
    assert latest_total == 8
