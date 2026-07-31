"""Unit coverage for read-only helpers in app.crud.policies."""

from __future__ import annotations

from datetime import date

from app.crud.policies import list_external_ids
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
