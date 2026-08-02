"""Re-run AI category classification for policies already in the database.

Generation mode never writes to the database: it reads every existing policy,
asks ``category_classifier.classify_policy_category`` for a fresh
category_codes list, and writes a review draft next to the seed drafts.
Approval mode only touches ``policy_categories`` (through
``crud.policies.replace_policy_categories``) - every other policy field,
plus conditions/documents/benefits, is left untouched.

Runs against whichever database ``DATABASE_URL`` points to when the process
starts (see app/core/config.py) - point it at MySQL or SQLite as needed.
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

from app.models.user_category_profile import CategoryCode
from app.services.ai.category_classifier import classify_policy_category
from app.services.ai.solar_client import SolarClient

SessionFactory = Callable[[], object]
ReplaceCategoriesFunction = Callable[..., None]

_ALLOWED_CATEGORY_CODES = frozenset(code.value for code in CategoryCode)


def _default_persistence_dependencies() -> tuple[SessionFactory, ReplaceCategoriesFunction]:
    """Resolve database code only when it is actually needed."""

    try:
        session_module = importlib.import_module("app.db.session")
        crud_module = importlib.import_module("app.crud.policies")
    except ImportError as exc:
        raise RuntimeError("this requires app.db.session and app.crud.policies") from exc
    session_factory = getattr(session_module, "SessionLocal", None)
    replace_categories = getattr(crud_module, "replace_policy_categories", None)
    if not callable(session_factory):
        raise RuntimeError("app.db.session.SessionLocal is not callable")
    if not callable(replace_categories):
        raise RuntimeError("app.crud.policies.replace_policy_categories is not callable")
    return (
        cast(SessionFactory, session_factory),
        cast(ReplaceCategoriesFunction, replace_categories),
    )


def _policy_payload_from_row(policy: object) -> dict[str, object]:
    """Build the dict shape classify_policy_category() expects from an ORM row."""

    return {
        "title": getattr(policy, "title", None),
        "support_target_text": getattr(policy, "support_target_text", None) or "",
        "support_content_text": getattr(policy, "support_content_text", None) or "",
        "raw_payload": getattr(policy, "raw_payload", None) or {},
    }


async def create_recategorize_draft(
    *,
    review_dir: str | Path | None = None,
    solar_client: SolarClient | None = None,
) -> Path:
    """Read every policy in the current DB and draft a fresh category_codes list."""

    session_module = importlib.import_module("app.db.session")
    crud_module = importlib.import_module("app.crud.policies")
    session = session_module.SessionLocal()

    owns_solar_client = solar_client is None
    ai_client = solar_client or SolarClient()
    bundles: list[dict[str, object]] = []
    try:
        policies = crud_module.list_all_policies(session)
        total = len(policies)
        for index, policy in enumerate(policies, start=1):
            print(f"[{index}/{total}] 처리 중: {policy.title}", flush=True)
            old_codes = [
                category.code for category in crud_module.list_policy_categories(session, policy.id)
            ]
            new_codes = await classify_policy_category(
                _policy_payload_from_row(policy),
                client=ai_client,
            )
            source = policy.source
            bundles.append(
                {
                    "policy_id": policy.id,
                    "source": source.value if hasattr(source, "value") else str(source),
                    "external_id": policy.external_id,
                    "title": policy.title,
                    "old_category_codes": old_codes,
                    "new_category_codes": new_codes,
                }
            )
    finally:
        session.close()
        if owns_solar_client:
            await ai_client.close()

    batch_id = uuid4().hex
    draft: dict[str, object] = {
        "schema_version": 1,
        "kind": "policy_recategorize_batch",
        "status": "pending_review",
        "batch_id": batch_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policies": bundles,
    }
    output_path = resolve_review_dir(review_dir) / f"recategorize-{batch_id}.json"
    _write_json_atomically(output_path, draft)
    return output_path


def _validate_recategorize_draft(payload: Mapping[str, object]) -> list[tuple[int, list[str]]]:
    if payload.get("schema_version") != 1:
        raise SeedDraftError("unsupported recategorize draft schema_version")
    if payload.get("kind") != "policy_recategorize_batch":
        raise SeedDraftError("draft kind must be policy_recategorize_batch")
    if payload.get("status") != "pending_review":
        raise SeedDraftError("draft status must be 'pending_review'")
    raw_policies = payload.get("policies")
    if (
        not isinstance(raw_policies, Sequence)
        or isinstance(raw_policies, (str, bytes, bytearray))
        or not raw_policies
    ):
        raise SeedDraftError("policies must be a non-empty array")

    validated: list[tuple[int, list[str]]] = []
    for index, item in enumerate(raw_policies):
        if not isinstance(item, Mapping):
            raise SeedDraftError(f"policies[{index}] must be an object")
        policy_id = item.get("policy_id")
        if not isinstance(policy_id, int) or isinstance(policy_id, bool):
            raise SeedDraftError(f"policies[{index}].policy_id must be an integer")
        codes = item.get("new_category_codes")
        if (
            not isinstance(codes, Sequence)
            or isinstance(codes, (str, bytes, bytearray))
            or not codes
        ):
            raise SeedDraftError(f"policies[{index}].new_category_codes must be a non-empty array")
        checked_codes: list[str] = []
        for code in codes:
            if not isinstance(code, str) or code not in _ALLOWED_CATEGORY_CODES:
                raise SeedDraftError(f"unsupported category_code: {code!r}")
            checked_codes.append(code)
        validated.append((policy_id, checked_codes))
    return validated


async def approve_recategorize_draft(
    draft_path: str | Path,
    *,
    review_dir: str | Path | None = None,
    session_factory: SessionFactory | None = None,
    replace_categories: ReplaceCategoriesFunction | None = None,
) -> int:
    """Apply one reviewed draft's category_codes - and nothing else - to the DB."""

    resolved_review_dir = resolve_review_dir(review_dir)
    approved_path = _path_inside_review_dir(Path(draft_path), resolved_review_dir)
    payload = load_json_file(approved_path)
    validated = _validate_recategorize_draft(payload)

    if session_factory is None or replace_categories is None:
        default_factory, default_replace = _default_persistence_dependencies()
        session_factory = session_factory or default_factory
        replace_categories = replace_categories or default_replace

    session = session_factory()
    try:
        for policy_id, codes in validated:
            replace_categories(session, policy_id=policy_id, category_codes=codes)
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
            "Re-run AI category classification for policies already in the database. "
            "Generation mode is read-only; --approve writes only policy_categories."
        )
    )
    parser.add_argument(
        "--approve",
        metavar="DRAFT_FILE",
        help="approve an existing recategorize draft; only policy_categories is written",
    )
    parser.add_argument(
        "--review-dir",
        help="draft directory (default: JOOP_REVIEW_DIR or ./review_drafts)",
    )
    return parser


async def async_main(args: argparse.Namespace) -> int:
    if args.approve:
        count = await approve_recategorize_draft(args.approve, review_dir=args.review_dir)
        print(f"Updated categories for {count} polic{'y' if count == 1 else 'ies'} through CRUD.")
        return 0
    draft_path = await create_recategorize_draft(review_dir=args.review_dir)
    print(f"Review draft created: {draft_path}")
    print("No database changes were made. Review the JSON, then use --approve.")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
