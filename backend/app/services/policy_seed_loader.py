"""Bootstrap policy data from git-committed, human-approved seed drafts.

Mirrors ``crud.categories.ensure_default_categories`` / ``ensure_default_category_questions``:
runs once per backend boot (gated by ``settings.auto_create_tables`` in
``app.main``'s lifespan) so every environment ends up with the same policy
data after ``git pull`` + a container restart. No AI/API calls happen here -
the drafts under ``review_drafts/`` were already collected, extracted, and
reviewed through ``scripts/seed_policy_data.py --approve`` before being
committed; this module only re-validates and upserts them.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.crud.policies import upsert_policy_bundle
from scripts.seed_policy_data import (
    database_ready_bundle,
    load_json_file,
    resolve_review_dir,
    validated_bundles,
)


def ensure_seeded_policies(
    db: Session,
    *,
    review_dir: str | Path | None = None,
) -> int:
    """Upsert every already-approved draft under the review directory.

    Drafts whose ``status`` is not ``"approved"`` (e.g. a ``pending_review``
    draft committed by mistake) are skipped rather than applied - only
    explicitly reviewed data ever reaches the database. Validation/DB errors
    are not swallowed: a broken committed draft should fail startup loudly,
    the same fail-fast philosophy as ``ensure_default_categories``.
    """

    directory = resolve_review_dir(review_dir)
    applied = 0
    for path in sorted(directory.glob("policy-seed-*.json")):
        payload = load_json_file(path)
        if payload.get("status") != "approved":
            continue
        bundles = validated_bundles(payload, expected_status="approved")
        for bundle in bundles:
            upsert_policy_bundle(db, database_ready_bundle(bundle))
            applied += 1
    return applied


__all__ = ["ensure_seeded_policies"]
