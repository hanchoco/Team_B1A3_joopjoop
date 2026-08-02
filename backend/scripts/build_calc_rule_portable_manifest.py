"""Build a portable calc-rule manifest from already-approved calc-rule-backfill
drafts, for use with sync_calc_rules_to_target.py.

calc-rule-backfill-*.json (written by backfill_calculation_rules.py) identifies
each entry by policy_id/benefit_id - primary keys local to whichever database
generated the draft. Those ids are meaningless (or actively dangerous to reuse)
against a different database instance such as Railway MySQL - see
sync_calc_rules_to_target.py's module docstring for why.

This script resolves each entry's policy_id -> (source, external_id) and its
benefit_display_text -> benefit_type by looking them up against whichever
database DATABASE_URL currently points to - run this against the SAME database
the calc-rule-backfill draft(s) were approved on (typically local), not the
target you intend to sync to. The output only contains content-derived,
portable identifiers, so sync_calc_rules_to_target.py can safely re-resolve
each entry against a completely different database afterwards.

Deliberately reads calculation_rule_json from the LIVE benefit row, not from
the draft file's frozen payload: if a value was hand-corrected directly in the
database after the draft was approved (e.g. clearing a wrong extraction), the
draft's own JSON still has the old, wrong value - only the live row has the
truth. Entries whose live value is null (nothing worth syncing - a correction
that concluded no attractable number exists) are dropped from the manifest.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.crud.policies import get_policy  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


class ManifestBuildError(Exception):
    """Raised when a calc-rule-backfill entry can't be resolved locally."""


def build_entries(draft_paths: list[str | Path]) -> list[dict[str, Any]]:
    db = SessionLocal()
    entries: list[dict[str, Any]] = []
    skipped_null = 0
    try:
        for path in draft_paths:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            if payload.get("kind") != "calc_rule_backfill_batch":
                raise ManifestBuildError(f"{path}: not a calc_rule_backfill_batch draft")
            for item in payload.get("policies", []):
                policy = get_policy(db, item["policy_id"])
                if policy is None:
                    raise ManifestBuildError(
                        f"{path}: policy_id={item['policy_id']} not found locally "
                        f"({item.get('policy_title')!r}) - run this against the same "
                        "database the draft was approved on"
                    )
                display_text = item["benefit_display_text"]
                matches = [b for b in policy.benefits if b.display_text == display_text]
                if len(matches) != 1:
                    raise ManifestBuildError(
                        f"{path}: benefit match count={len(matches)} in policy "
                        f"{policy.title!r} for display_text={display_text!r} - expected 1"
                    )
                benefit = matches[0]
                current_rule = benefit.calculation_rule_json
                if not current_rule:
                    # Corrected to null locally after the draft was approved
                    # (e.g. a disambiguation bug fix) - nothing worth syncing.
                    skipped_null += 1
                    continue
                entries.append(
                    {
                        "source": policy.source.value,
                        "external_id": policy.external_id,
                        "policy_title": policy.title,
                        "benefit_type": benefit.benefit_type.value,
                        "benefit_display_text": display_text,
                        "calc_type": item["calc_type"],
                        "calculation_rule_json": current_rule,
                    }
                )
    finally:
        db.close()
    if skipped_null:
        print(
            f"참고: {skipped_null}건은 draft 승인 이후 로컬 DB에서 null로 정정되어 "
            "manifest에서 제외했습니다."
        )
    return entries


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "drafts",
        nargs="+",
        help="one or more approved calc-rule-backfill-*.json paths",
    )
    parser.add_argument(
        "--output",
        default="review_drafts/calc-rule-portable-manifest.json",
        help="output path (default: review_drafts/calc-rule-portable-manifest.json)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        entries = build_entries(args.drafts)
    except ManifestBuildError as exc:
        print(f"중단: {exc}", file=sys.stderr)
        return 1

    manifest = {
        "schema_version": 1,
        "kind": "calc_rule_portable_manifest",
        "generated_at": datetime.now(UTC).isoformat(),
        "generated_from": [str(p) for p in args.drafts],
        "entries": entries,
    }
    output_path = Path(args.output)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"작성 완료: {output_path} ({len(entries)}건)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
