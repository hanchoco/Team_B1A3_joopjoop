"""Backfill PolicyBenefit.calculation_rule_json for benefits already in the database.

Generation mode never writes to the database: it reads every existing policy,
resolves each benefit's CalcType with resolve_calc_type() (using the real ORM
Policy/PolicyBenefit objects - no adapter needed, unlike the fresh-extraction
pipeline in seed_policy_data.py where those objects don't exist yet), skips
benefits with no CalcType (SERVICE/OTHER) or that already have a
calculation_rule_json, and asks extract_calculation_rule() to fill the rest.
Approval mode only touches calculation_rule_json (through
crud.policies.update_benefit_calculation_rule) - every other field is left
untouched.

IMPORTANT - this DB write does not necessarily survive a reboot. app.main's
lifespan calls policy_seed_loader.ensure_seeded_policies() on every startup,
which re-upserts every approved review_drafts/policy-seed-*.json through
crud.upsert_policy_bundle() -> _replace_policy_children(), a full DELETE+
re-INSERT of that policy's policy_benefits rows (new primary keys each time).
For any policy whose seed draft file still exists, the next boot silently
resets calculation_rule_json back to null and this row's id changes, orphaning
the update this script just made. If a backfilled value needs to survive
reboots, patch the same benefit entry (matched by external_id + display_text,
never by benefit_id/policy_id - those are not stable across replays) inside
its source review_drafts/policy-seed-*.json file too, not just the DB.

Runs against whichever database DATABASE_URL points to when the process
starts (see app/core/config.py).
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import asyncio
import importlib
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import cast
from uuid import uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from seed_policy_data import (  # same directory - shared draft I/O helpers
    SeedDraftError,
    _path_inside_review_dir,
    _write_json_atomically,
    load_json_file,
    resolve_review_dir,
)

from app.models.policy import CalcType
from app.services.ai.calc_rule_extractor import (
    extract_calculation_rule,
    is_calculation_rule_complete,
)
from app.services.ai.solar_client import SolarClient
from app.services.policy_engine.calc_type import resolve_calc_type

SessionFactory = Callable[[], object]
UpdateRuleFunction = Callable[..., None]

_ALLOWED_CALC_TYPES = frozenset(calc_type.value for calc_type in CalcType)


def _default_persistence_dependencies() -> tuple[SessionFactory, UpdateRuleFunction]:
    """Resolve database code only when it is actually needed."""

    try:
        session_module = importlib.import_module("app.db.session")
        crud_module = importlib.import_module("app.crud.policies")
    except ImportError as exc:
        raise RuntimeError("this requires app.db.session and app.crud.policies") from exc
    session_factory = getattr(session_module, "SessionLocal", None)
    update_rule = getattr(crud_module, "update_benefit_calculation_rule", None)
    if not callable(session_factory):
        raise RuntimeError("app.db.session.SessionLocal is not callable")
    if not callable(update_rule):
        raise RuntimeError("app.crud.policies.update_benefit_calculation_rule is not callable")
    return (
        cast(SessionFactory, session_factory),
        cast(UpdateRuleFunction, update_rule),
    )


def _policy_payload_from_row(policy: object) -> dict[str, object]:
    """Build the dict shape extract_calculation_rule() expects from an ORM row."""

    return {
        "title": getattr(policy, "title", None),
        "support_content_text": getattr(policy, "support_content_text", None) or "",
        "raw_payload": getattr(policy, "raw_payload", None) or {},
    }


async def create_calc_rule_backfill_draft(
    *,
    review_dir: str | Path | None = None,
    solar_client: SolarClient | None = None,
) -> Path:
    """Read every policy's benefits and draft calculation_rule_json for the eligible ones."""

    session_module = importlib.import_module("app.db.session")
    crud_module = importlib.import_module("app.crud.policies")
    session = session_module.SessionLocal()

    owns_solar_client = solar_client is None
    ai_client = solar_client or SolarClient()
    bundles: list[dict[str, object]] = []
    skipped_no_calc_type = 0
    skipped_already_filled = 0
    skipped_incomplete = 0
    try:
        policies = crud_module.list_all_policies(session)
        for policy in policies:
            policy_payload = _policy_payload_from_row(policy)
            for benefit in policy.benefits:
                if benefit.calculation_rule_json:
                    skipped_already_filled += 1
                    continue
                calc_type = resolve_calc_type(benefit, policy)
                if calc_type is None:
                    skipped_no_calc_type += 1
                    continue
                print(
                    f"처리 중: [{policy.title}] {benefit.display_text} "
                    f"(calc_type={calc_type.value})",
                    flush=True,
                )
                rule = await extract_calculation_rule(
                    policy_payload,
                    calc_type=calc_type,
                    client=ai_client,
                    benefit_display_text=benefit.display_text,
                )
                if rule is None:
                    skipped_incomplete += 1
                    continue
                bundles.append(
                    {
                        "benefit_id": benefit.id,
                        "policy_id": policy.id,
                        "policy_title": policy.title,
                        "benefit_display_text": benefit.display_text,
                        "calc_type": calc_type.value,
                        "calculation_rule_json": rule,
                    }
                )
    finally:
        session.close()
        if owns_solar_client:
            await ai_client.close()

    print(
        f"완료: {len(bundles)}건 채움, {skipped_no_calc_type}건 CalcType 없음(SERVICE/OTHER), "
        f"{skipped_already_filled}건 이미 채워짐, {skipped_incomplete}건 필수 필드 부족으로 보류",
        flush=True,
    )

    batch_id = uuid4().hex
    draft: dict[str, object] = {
        "schema_version": 1,
        "kind": "calc_rule_backfill_batch",
        "status": "pending_review",
        "batch_id": batch_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policies": bundles,
    }
    output_path = resolve_review_dir(review_dir) / f"calc-rule-backfill-{batch_id}.json"
    _write_json_atomically(output_path, draft)
    return output_path


def _validate_backfill_draft(payload: Mapping[str, object]) -> list[tuple[int, dict[str, object]]]:
    if payload.get("schema_version") != 1:
        raise SeedDraftError("unsupported backfill draft schema_version")
    if payload.get("kind") != "calc_rule_backfill_batch":
        raise SeedDraftError("draft kind must be calc_rule_backfill_batch")
    if payload.get("status") != "pending_review":
        raise SeedDraftError("draft status must be 'pending_review'")
    raw_policies = payload.get("policies")
    if not isinstance(raw_policies, Sequence) or isinstance(raw_policies, (str, bytes, bytearray)):
        raise SeedDraftError("policies must be an array")

    validated: list[tuple[int, dict[str, object]]] = []
    for index, item in enumerate(raw_policies):
        if not isinstance(item, Mapping):
            raise SeedDraftError(f"policies[{index}] must be an object")
        benefit_id = item.get("benefit_id")
        if not isinstance(benefit_id, int) or isinstance(benefit_id, bool):
            raise SeedDraftError(f"policies[{index}].benefit_id must be an integer")
        rule = item.get("calculation_rule_json")
        if not isinstance(rule, Mapping):
            raise SeedDraftError(f"policies[{index}].calculation_rule_json must be an object")
        rule_type = rule.get("type")
        if rule_type not in _ALLOWED_CALC_TYPES:
            raise SeedDraftError(f"unsupported calculation_rule_json.type: {rule_type!r}")
        if not is_calculation_rule_complete(CalcType(rule_type), dict(rule)):
            raise SeedDraftError(
                f"policies[{index}] calculation_rule_json is missing required fields "
                f"for {rule_type}"
            )
        validated.append((benefit_id, dict(rule)))
    return validated


async def approve_calc_rule_backfill_draft(
    draft_path: str | Path,
    *,
    review_dir: str | Path | None = None,
    session_factory: SessionFactory | None = None,
    update_rule: UpdateRuleFunction | None = None,
) -> int:
    """Apply one reviewed draft's calculation_rule_json values - and nothing else."""

    resolved_review_dir = resolve_review_dir(review_dir)
    approved_path = _path_inside_review_dir(Path(draft_path), resolved_review_dir)
    payload = load_json_file(approved_path)
    validated = _validate_backfill_draft(payload)

    if session_factory is None or update_rule is None:
        default_factory, default_update = _default_persistence_dependencies()
        session_factory = session_factory or default_factory
        update_rule = update_rule or default_update

    session = session_factory()
    try:
        for benefit_id, rule in validated:
            update_rule(session, benefit_id=benefit_id, calculation_rule_json=rule)
        commit = getattr(session, "commit", None)
        if callable(commit):
            commit()
    finally:
        close_method = getattr(session, "close", None)
        if callable(close_method):
            close_method()

    approved_payload = dict(payload)
    approved_payload["status"] = "approved"
    approved_payload["approved_at"] = datetime.now(timezone.utc).isoformat()
    _write_json_atomically(approved_path, approved_payload)
    return len(validated)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill calculation_rule_json for policy_benefits already in the database. "
            "Generation mode is read-only; --approve writes only calculation_rule_json."
        )
    )
    parser.add_argument(
        "--approve",
        metavar="DRAFT_FILE",
        help="approve an existing backfill draft; only calculation_rule_json is written",
    )
    parser.add_argument(
        "--review-dir",
        help="draft directory (default: JOOP_REVIEW_DIR or ./review_drafts)",
    )
    return parser


async def async_main(args: argparse.Namespace) -> int:
    if args.approve:
        count = await approve_calc_rule_backfill_draft(args.approve, review_dir=args.review_dir)
        print(f"Updated calculation_rule_json for {count} benefit(s) through CRUD.")
        return 0
    draft_path = await create_calc_rule_backfill_draft(review_dir=args.review_dir)
    print(f"Review draft created: {draft_path}")
    print("No database changes were made. Review the JSON, then use --approve.")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
