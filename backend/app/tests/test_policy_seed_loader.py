"""Tests for auto-loading git-committed, approved policy seed drafts at boot."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.crud.policies import list_external_ids
from app.db.session import SessionLocal
from app.services.policy_seed_loader import ensure_seeded_policies


def _draft(*, status: str, external_id: str = "seed-loader-test-1") -> dict:
    policy = {
        "source": "ONTONG_YOUTH",
        "external_id": external_id,
        "title": "청년 월세 지원",
        "summary": "",
        "description": "",
        "support_target_text": "",
        "support_content_text": "",
        "application_method": "",
        "provider_name": "",
        "application_url": "",
        "status": "ACTIVE",
        "subcategory": "",
        "region_scope": "",
        "region_code": "",
        "contact": "",
        "original_text": "",
        "application_start_date": None,
        "application_end_date": None,
        "published_date": None,
        "is_ongoing": False,
        "is_active": True,
        "raw_payload": {"plcyNm": "청년 월세 지원"},
        "source_updated_at": datetime.now(timezone.utc).isoformat(),
    }
    return {
        "schema_version": 1,
        "kind": "policy_seed_batch",
        "status": status,
        "policies": [
            {
                "policy": policy,
                "conditions": [],
                "documents": [],
                "benefits": [],
                "category_codes": ["HOUSING"],
            }
        ],
    }


def _write_draft(directory: Path, name: str, draft: dict) -> None:
    (directory / name).write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")


def test_ensure_seeded_policies_applies_approved_draft_and_is_idempotent(
    tmp_path: Path,
) -> None:
    _write_draft(tmp_path, "policy-seed-1.json", _draft(status="approved"))

    with SessionLocal() as db:
        applied = ensure_seeded_policies(db, review_dir=tmp_path)
        assert applied == 1
        assert "seed-loader-test-1" in list_external_ids(db, source="ONTONG_YOUTH")

        # Re-running on boot again (e.g. container restart) must not duplicate.
        applied_again = ensure_seeded_policies(db, review_dir=tmp_path)
        assert applied_again == 1
        assert len(list_external_ids(db, source="ONTONG_YOUTH")) == 1


def test_ensure_seeded_policies_skips_pending_review_draft(tmp_path: Path) -> None:
    _write_draft(tmp_path, "policy-seed-2.json", _draft(status="pending_review"))

    with SessionLocal() as db:
        applied = ensure_seeded_policies(db, review_dir=tmp_path)
        assert applied == 0
        assert list_external_ids(db, source="ONTONG_YOUTH") == set()


def test_ensure_seeded_policies_is_a_noop_on_an_empty_directory(tmp_path: Path) -> None:
    with SessionLocal() as db:
        assert ensure_seeded_policies(db, review_dir=tmp_path) == 0
