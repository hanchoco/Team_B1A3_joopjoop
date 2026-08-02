"""Reapply an already-approved calc-rule-backfill batch to a DIFFERENT database
instance (e.g. Railway MySQL) than the one it was generated/approved against.

Why this exists: approve_calc_rule_backfill_draft() in backfill_calculation_rules.py
writes by benefit_id, a local auto-increment primary key with no meaning across
database instances - or even across reboots of the SAME instance, since
policy_seed_loader.ensure_seeded_policies() replays every approved
review_drafts/policy-seed-*.json on every boot via crud._replace_policy_children(),
a delete+reinsert that assigns fresh ids each time. Reusing a benefit_id captured
on one database against another database risks silently overwriting an unrelated
row that happens to share that numeric id.

Input is a "portable manifest" (schema_version 1, kind calc_rule_portable_manifest)
where each entry identifies its target by (source, external_id) for the policy and
(benefit_type, benefit_display_text) for the benefit - content-derived, stable
identifiers - instead of any numeric id. Build one from existing approved
calc-rule-backfill-*.json drafts with build_calc_rule_portable_manifest.py
(run against the database those drafts were originally approved on, so their
local policy_id/benefit_id can still be resolved).

Safety guarantees:
- dry-run by default; --apply is required to write anything.
- a policy or benefit match count other than exactly 1 aborts the ENTIRE run
  before anything is written (no partial application of a batch).
- only calculation_rule_json is ever touched, through
  crud.policies.update_benefit_calculation_rule (same function the ordinary
  backfill approval flow uses) - never benefit_type/amount_type/display_text/etc.
- every matched benefit_id + policy title is printed before any write.
- entries whose target calculation_rule_json already equals the new value are
  skipped (not re-written, not counted as a change).
- the whole batch is one transaction: a single commit at the end if every
  entry resolved and applied cleanly, otherwise a rollback and nothing written.

Run against whichever database DATABASE_URL points to when the process starts
(see app/core/config.py) - point it at Railway's MySQL before running.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.crud.policies import update_benefit_calculation_rule  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.policy import Policy, PolicyBenefit  # noqa: E402


class SyncError(Exception):
    """Raised when a manifest entry can't be uniquely and safely matched."""


def load_manifest(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise SyncError("unsupported manifest schema_version")
    if payload.get("kind") != "calc_rule_portable_manifest":
        raise SyncError("manifest kind must be calc_rule_portable_manifest")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise SyncError("manifest.entries must be a list")
    return entries


def resolve_benefit(db: Session, entry: Mapping[str, Any]) -> PolicyBenefit:
    """Find the one benefit this entry targets, or abort - never guess."""

    external_id = entry.get("external_id")
    source = entry.get("source")
    policies = list(
        db.scalars(
            select(Policy).where(Policy.source == source, Policy.external_id == external_id)
        ).all()
    )
    if len(policies) != 1:
        raise SyncError(
            f"policy match count={len(policies)} for external_id={external_id!r} "
            f"({entry.get('policy_title')!r}) - expected exactly 1, aborting"
        )
    policy = policies[0]

    benefit_type = entry.get("benefit_type")
    display_text = entry.get("benefit_display_text")
    benefits = [
        b
        for b in policy.benefits
        if b.benefit_type.value == benefit_type and b.display_text == display_text
    ]
    if len(benefits) != 1:
        raise SyncError(
            f"benefit match count={len(benefits)} within policy {policy.title!r} "
            f"(external_id={external_id!r}) for display_text={display_text!r} - "
            f"expected exactly 1, aborting"
        )
    return benefits[0]


def run(manifest_path: str | Path, *, apply: bool) -> int:
    entries = load_manifest(manifest_path)
    db = SessionLocal()
    applied = 0
    skipped = 0
    try:
        planned: list[tuple[int, str, dict[str, Any] | None]] = []
        for entry in entries:
            benefit = resolve_benefit(db, entry)
            new_rule = entry.get("calculation_rule_json")
            policy_title = entry.get("policy_title", "")

            if benefit.calculation_rule_json == new_rule:
                print(f"[SKIP] benefit_id={benefit.id} ({policy_title}) - 이미 동일한 값")
                skipped += 1
                continue

            print(
                f"[{'APPLY' if apply else 'DRY-RUN'}] benefit_id={benefit.id} "
                f"policy={policy_title!r} display_text={entry.get('benefit_display_text')!r}"
            )
            planned.append((benefit.id, policy_title, new_rule))

        if not apply:
            print(
                f"\n총 {len(planned)}건 변경 예정, {skipped}건 이미 동일 - "
                "dry-run이라 아무것도 반영되지 않았습니다."
            )
            print("실제로 반영하려면 --apply 옵션을 추가해서 다시 실행하세요.")
            return 0

        for benefit_id, _policy_title, new_rule in planned:
            update_benefit_calculation_rule(
                db, benefit_id=benefit_id, calculation_rule_json=new_rule
            )
        db.commit()
        applied = len(planned)
        print(f"\n완료: {applied}건 반영, {skipped}건 이미 동일해서 건너뜀")
        return applied
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reapply a calc_rule_portable_manifest to whichever database "
            "DATABASE_URL points to, matching by (source, external_id) + "
            "(benefit_type, display_text) instead of numeric ids that don't "
            "carry over between database instances."
        )
    )
    parser.add_argument("manifest", help="path to a calc-rule-portable-manifest.json file")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually write to the database (default: dry-run, no writes)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        run(args.manifest, apply=args.apply)
    except SyncError as exc:
        print(f"중단: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
