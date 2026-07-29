"""Collect policies, create AI review drafts, and approve reviewed batches.

Collection mode never writes to the database. Approval mode never calls the
external APIs; it only persists a named, already-reviewed draft through
``app.crud.policies.upsert_policy_bundle``.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import asyncio
import importlib
import inspect
import json
import os
import sys
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import date, datetime, timezone
from pathlib import Path
from typing import cast
from uuid import uuid4

# ``python scripts/seed_policy_data.py`` must resolve the backend's ``app``
# package even when Python makes ``scripts`` the first import directory.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.integrations.youth_policy_api import YouthPolicyClient
from app.services.ai.checklist_generator import (
    generate_checklist,
    validate_checklist_payload,
)
from app.services.ai.rule_extractor import (
    extract_conditions,
    validate_condition_payload,
)
from app.services.ai.solar_client import SolarClient

SessionFactory = Callable[[], object]
UpsertFunction = Callable[[object, Mapping[str, object]], object]

_POLICY_STRING_FIELDS = frozenset(
    {
        "source",
        "external_id",
        "title",
        "summary",
        "description",
        "support_target_text",
        "support_content_text",
        "application_method",
        "provider_name",
        "application_url",
        "status",
        "subcategory",
        "region_scope",
        "region_code",
        "contact",
        "original_text",
    }
)
_POLICY_DATE_FIELDS = (
    "application_start_date",
    "application_end_date",
    "published_date",
)
_ALLOWED_SOURCES = frozenset({"ONTONG_YOUTH", "MANUAL"})
_ALLOWED_STATUSES = frozenset({"DRAFT", "ACTIVE", "CLOSED", "ARCHIVED"})
_MAX_DRAFT_BYTES = 50 * 1024 * 1024


class SeedDraftError(ValueError):
    """Raised when a review batch is missing, unsafe, or malformed."""


def resolve_review_dir(review_dir: str | Path | None = None) -> Path:
    """Resolve a configurable draft directory relative to the execution CWD."""

    configured = (
        Path(review_dir)
        if review_dir is not None
        else Path(os.getenv("JOOP_REVIEW_DIR", Path.cwd() / "review_drafts"))
    )
    resolved = configured.expanduser().resolve()
    if resolved == Path(resolved.anchor):
        raise SeedDraftError("review directory must not be a filesystem root")
    resolved.mkdir(parents=True, exist_ok=True)
    if not resolved.is_dir():
        raise SeedDraftError("review directory must be a directory")
    return resolved


def _write_json_atomically(
    path: Path,
    payload: Mapping[str, object],
) -> None:
    temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary_path.replace(path)


def _path_inside_review_dir(path: Path, review_dir: Path) -> Path:
    candidate = path.expanduser()
    if not candidate.is_absolute() and candidate.parent == Path("."):
        candidate = review_dir / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(review_dir)
    except ValueError as exc:
        raise SeedDraftError(
            "approval draft must be inside the configured review directory"
        ) from exc
    return resolved


def _load_json_file(path: Path) -> Mapping[str, object]:
    if not path.is_file():
        raise SeedDraftError(f"review draft not found: {path}")
    if path.stat().st_size > _MAX_DRAFT_BYTES:
        raise SeedDraftError("review draft is too large")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SeedDraftError("review draft must be valid UTF-8 JSON") from exc
    if not isinstance(payload, Mapping):
        raise SeedDraftError("review draft must be a JSON object")
    return payload


def _require_policy_string(
    policy: Mapping[str, object],
    field: str,
    *,
    allow_empty: bool,
) -> str:
    value = policy.get(field)
    if not isinstance(value, str):
        raise SeedDraftError(f"policy.{field} must be a string")
    normalized = value.strip()
    if not allow_empty and not normalized:
        raise SeedDraftError(f"policy.{field} must not be empty")
    return normalized


def _validate_date_string(
    policy: Mapping[str, object],
    field: str,
) -> str | None:
    value = policy.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise SeedDraftError(f"policy.{field} must be an ISO date or null")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise SeedDraftError(f"policy.{field} must be an ISO date") from exc


def _validate_policy(policy: object) -> dict[str, object]:
    if not isinstance(policy, Mapping):
        raise SeedDraftError("policy must be an object")
    validated = dict(policy)
    for field in _POLICY_STRING_FIELDS:
        if field not in policy:
            if field in {"source", "external_id", "title", "status"}:
                raise SeedDraftError(f"policy.{field} is required")
            validated[field] = ""
            continue
        validated[field] = _require_policy_string(
            policy,
            field,
            allow_empty=field not in {"source", "external_id", "title", "status"},
        )
    if validated["source"] not in _ALLOWED_SOURCES:
        raise SeedDraftError("policy.source is unsupported")
    if validated["status"] not in _ALLOWED_STATUSES:
        raise SeedDraftError("policy.status is unsupported")

    for field in _POLICY_DATE_FIELDS:
        validated[field] = _validate_date_string(policy, field)
    for field in ("is_ongoing", "is_active"):
        value = policy.get(field)
        if not isinstance(value, bool):
            raise SeedDraftError(f"policy.{field} must be boolean")
        validated[field] = value
    raw_payload = policy.get("raw_payload")
    if not isinstance(raw_payload, Mapping):
        raise SeedDraftError("policy.raw_payload must be an object")
    try:
        validated["raw_payload"] = json.loads(
            json.dumps(raw_payload, ensure_ascii=False, allow_nan=False)
        )
    except (TypeError, ValueError) as exc:
        raise SeedDraftError("policy.raw_payload must be valid JSON") from exc
    source_updated_at = policy.get("source_updated_at")
    if not isinstance(source_updated_at, str):
        raise SeedDraftError("policy.source_updated_at must be an ISO datetime")
    try:
        datetime.fromisoformat(source_updated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SeedDraftError("policy.source_updated_at must be an ISO datetime") from exc
    validated["source_updated_at"] = source_updated_at
    return validated


def _validated_bundles(
    payload: Mapping[str, object],
) -> list[dict[str, object]]:
    if payload.get("schema_version") != 1:
        raise SeedDraftError("unsupported seed draft schema_version")
    if payload.get("kind") != "policy_seed_batch":
        raise SeedDraftError("draft kind must be policy_seed_batch")
    if payload.get("status") != "pending_review":
        raise SeedDraftError("only pending_review drafts can be approved")
    raw_policies = payload.get("policies")
    if (
        not isinstance(raw_policies, Sequence)
        or isinstance(raw_policies, (str, bytes, bytearray))
        or not raw_policies
    ):
        raise SeedDraftError("policies must be a non-empty array")

    bundles: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for index, raw_bundle in enumerate(raw_policies):
        if not isinstance(raw_bundle, Mapping):
            raise SeedDraftError(f"policies[{index}] must be an object")
        policy = _validate_policy(raw_bundle.get("policy"))
        identity = (str(policy["source"]), str(policy["external_id"]))
        if identity in seen:
            raise SeedDraftError(f"policies[{index}] duplicates source/external_id")
        seen.add(identity)
        conditions = validate_condition_payload({"conditions": raw_bundle.get("conditions")})
        documents = validate_checklist_payload({"documents": raw_bundle.get("documents")})
        bundle = dict(policy)
        bundle["conditions"] = [condition.to_dict() for condition in conditions]
        bundle["documents"] = [document.to_dict() for document in documents]
        bundles.append(bundle)
    return bundles


def _database_ready_bundle(bundle: Mapping[str, object]) -> dict[str, object]:
    ready = dict(bundle)
    for field in _POLICY_DATE_FIELDS:
        value = ready.get(field)
        if isinstance(value, str):
            ready[field] = date.fromisoformat(value)
    source_updated_at = ready.get("source_updated_at")
    if isinstance(source_updated_at, str):
        parsed = datetime.fromisoformat(source_updated_at.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        ready["source_updated_at"] = parsed
    return ready


def _default_persistence_dependencies() -> tuple[SessionFactory, UpsertFunction]:
    """Resolve database code only for explicit approval mode."""

    try:
        session_module = importlib.import_module("app.db.session")
        crud_module = importlib.import_module("app.crud.policies")
    except ImportError as exc:
        raise RuntimeError("approval requires app.db.session and app.crud.policies") from exc
    session_factory = getattr(session_module, "SessionLocal", None)
    upsert_function = getattr(crud_module, "upsert_policy_bundle", None)
    if not callable(session_factory):
        raise RuntimeError("app.db.session.SessionLocal is not callable")
    if not callable(upsert_function):
        raise RuntimeError("app.crud.policies.upsert_policy_bundle is not callable")
    return (
        cast(SessionFactory, session_factory),
        cast(UpsertFunction, upsert_function),
    )


async def _call_upsert(
    upsert_function: UpsertFunction,
    session: object,
    bundle: Mapping[str, object],
) -> None:
    result = upsert_function(session, bundle)
    if inspect.isawaitable(result):
        await cast(Awaitable[object], result)


async def approve_seed_draft(
    draft_path: str | Path,
    *,
    review_dir: str | Path | None = None,
    session_factory: SessionFactory | None = None,
    upsert_function: UpsertFunction | None = None,
) -> int:
    """Persist one explicitly named, pending draft exclusively through CRUD."""

    resolved_review_dir = resolve_review_dir(review_dir)
    approved_path = _path_inside_review_dir(
        Path(draft_path),
        resolved_review_dir,
    )
    payload = _load_json_file(approved_path)
    bundles = _validated_bundles(payload)

    if session_factory is None or upsert_function is None:
        default_factory, default_upsert = _default_persistence_dependencies()
        session_factory = session_factory or default_factory
        upsert_function = upsert_function or default_upsert

    session = session_factory()
    try:
        for bundle in bundles:
            await _call_upsert(
                upsert_function,
                session,
                _database_ready_bundle(bundle),
            )
    finally:
        close_method = getattr(session, "close", None)
        if callable(close_method):
            close_method()

    approved_payload = dict(payload)
    approved_payload["status"] = "approved"
    approved_payload["approved_at"] = datetime.now(timezone.utc).isoformat()
    _write_json_atomically(approved_path, approved_payload)
    return len(bundles)


async def create_seed_draft(
    *,
    review_dir: str | Path | None = None,
    page_size: int = 100,
    max_pages: int = 10,
    limit: int | None = 20,
    filters: Mapping[str, str] | None = None,
    youth_client: YouthPolicyClient | None = None,
    solar_client: SolarClient | None = None,
) -> Path:
    """Run collect -> extract -> checklist and write a pending review batch."""

    owns_youth_client = youth_client is None
    owns_solar_client = solar_client is None
    policy_client = youth_client or YouthPolicyClient()
    ai_client = solar_client or SolarClient()
    try:
        policies = await policy_client.collect(
            page_size=page_size,
            max_pages=max_pages,
            limit=limit,
            filters=filters,
        )
        if not policies:
            raise SeedDraftError("the youth policy API returned no policies")
        bundles: list[dict[str, object]] = []
        for policy in policies:
            policy_payload = policy.to_dict()
            conditions = await extract_conditions(
                policy_payload,
                client=ai_client,
            )
            documents = await generate_checklist(
                policy_payload,
                client=ai_client,
            )
            bundles.append(
                {
                    "policy": policy_payload,
                    "conditions": [condition.to_dict() for condition in conditions],
                    "documents": [document.to_dict() for document in documents],
                }
            )
    finally:
        if owns_youth_client:
            await policy_client.close()
        if owns_solar_client:
            await ai_client.close()

    batch_id = uuid4().hex
    draft: dict[str, object] = {
        "schema_version": 1,
        "kind": "policy_seed_batch",
        "status": "pending_review",
        "batch_id": batch_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "ONTONG_YOUTH",
        "policies": bundles,
    }
    output_path = resolve_review_dir(review_dir) / f"policy-seed-{batch_id}.json"
    _write_json_atomically(output_path, draft)
    return output_path


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create review-only policy drafts, or explicitly approve one "
            "existing draft through the CRUD layer."
        )
    )
    parser.add_argument(
        "--approve",
        metavar="DRAFT_FILE",
        help="approve an existing draft; collection and AI calls are skipped",
    )
    parser.add_argument(
        "--review-dir",
        help="draft directory (default: JOOP_REVIEW_DIR or ./review_drafts)",
    )
    parser.add_argument("--page-size", type=_positive_int, default=100)
    parser.add_argument("--max-pages", type=_positive_int, default=10)
    parser.add_argument(
        "--limit",
        type=_positive_int,
        default=20,
        help="maximum policies per draft (default: 20)",
    )
    parser.add_argument("--query")
    parser.add_argument("--category-code")
    parser.add_argument("--region-code")
    parser.add_argument("--keyword")
    return parser


def _filters_from_args(args: argparse.Namespace) -> dict[str, str]:
    values = {
        "query": args.query,
        "bizTycdSel": args.category_code,
        "srchPolyBizSecd": args.region_code,
        "keyword": args.keyword,
    }
    return {
        key: value.strip()
        for key, value in values.items()
        if isinstance(value, str) and value.strip()
    }


async def async_main(args: argparse.Namespace) -> int:
    if args.approve:
        count = await approve_seed_draft(
            args.approve,
            review_dir=args.review_dir,
        )
        print(f"Approved {count} policy bundle(s) through CRUD.")
        return 0
    draft_path = await create_seed_draft(
        review_dir=args.review_dir,
        page_size=args.page_size,
        max_pages=args.max_pages,
        limit=args.limit,
        filters=_filters_from_args(args),
    )
    print(f"Review draft created: {draft_path}")
    print("No database changes were made. Review the JSON, then use --approve.")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
