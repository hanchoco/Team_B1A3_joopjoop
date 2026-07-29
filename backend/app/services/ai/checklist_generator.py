"""Validated policy-document generation with review-only draft output."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from .prompt_templates import build_checklist_messages
from .solar_client import SolarClient

_DOCUMENT_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,49}$")
_MAX_RESPONSE_CHARACTERS = 1_000_000


class ChecklistValidationError(ValueError):
    """Raised when generated checklist JSON does not match the review schema."""


@dataclass(frozen=True, slots=True)
class GeneratedDocument:
    """One validated draft row for ``PolicyDocument``."""

    document_code: str
    document_name: str
    required_reason: str
    issuing_organization: str
    issuing_method: str
    issuing_url: str
    submission_format: str
    is_required: bool
    display_order: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) < 3 or not lines[-1].strip().startswith("```"):
        raise ChecklistValidationError("unterminated JSON code fence")
    return "\n".join(lines[1:-1]).strip()


def _parse_json_object(text: str) -> Mapping[str, object]:
    if not text.strip():
        raise ChecklistValidationError("AI response is empty")
    if len(text) > _MAX_RESPONSE_CHARACTERS:
        raise ChecklistValidationError("AI response is too large")
    try:
        payload = json.loads(_strip_json_fence(text))
    except json.JSONDecodeError as exc:
        raise ChecklistValidationError("AI response is not valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise ChecklistValidationError("AI response must be a JSON object")
    return payload


def _required_string(
    item: Mapping[str, object],
    key: str,
    *,
    allow_empty: bool = False,
    max_length: int | None = None,
) -> str:
    value = item.get(key)
    if not isinstance(value, str):
        raise ChecklistValidationError(f"{key} must be a string")
    normalized = value.strip()
    if not allow_empty and not normalized:
        raise ChecklistValidationError(f"{key} must not be empty")
    if max_length is not None and len(normalized) > max_length:
        raise ChecklistValidationError(f"{key} must be at most {max_length} characters")
    return normalized


def _required_int(
    item: Mapping[str, object],
    key: str,
    *,
    minimum: int,
) -> int:
    value = item.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ChecklistValidationError(f"{key} must be an integer")
    if value < minimum:
        raise ChecklistValidationError(f"{key} must be at least {minimum}")
    return value


def _required_bool(item: Mapping[str, object], key: str) -> bool:
    value = item.get(key)
    if not isinstance(value, bool):
        raise ChecklistValidationError(f"{key} must be a boolean")
    return value


def _validate_url(url: str, *, index: int) -> str:
    if not url:
        return url
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ChecklistValidationError(f"documents[{index}].issuing_url must be an HTTP(S) URL")
    return url


def validate_checklist_payload(payload: object) -> list[GeneratedDocument]:
    """Validate a decoded ``{"documents": [...]}`` payload."""

    if not isinstance(payload, Mapping):
        raise ChecklistValidationError("checklist payload must be an object")
    raw_documents = payload.get("documents")
    if not isinstance(raw_documents, Sequence) or isinstance(
        raw_documents, (str, bytes, bytearray)
    ):
        raise ChecklistValidationError("documents must be an array")

    documents: list[GeneratedDocument] = []
    seen_codes: set[str] = set()
    seen_names: set[str] = set()
    for index, raw_document in enumerate(raw_documents):
        if not isinstance(raw_document, Mapping):
            raise ChecklistValidationError(f"documents[{index}] must be an object")
        document_code = _required_string(raw_document, "document_code").upper()
        if not _DOCUMENT_CODE_PATTERN.fullmatch(document_code):
            raise ChecklistValidationError(f"documents[{index}].document_code is invalid")
        document_name = _required_string(
            raw_document,
            "document_name",
            max_length=255,
        )
        if document_code in seen_codes or document_name in seen_names:
            raise ChecklistValidationError(f"documents[{index}] duplicates a prior document")
        seen_codes.add(document_code)
        seen_names.add(document_name)
        issuing_url = _required_string(
            raw_document,
            "issuing_url",
            allow_empty=True,
            max_length=1_000,
        )
        documents.append(
            GeneratedDocument(
                document_code=document_code,
                document_name=document_name,
                required_reason=_required_string(
                    raw_document,
                    "required_reason",
                    allow_empty=True,
                    max_length=500,
                ),
                issuing_organization=_required_string(
                    raw_document,
                    "issuing_organization",
                    allow_empty=True,
                    max_length=255,
                ),
                issuing_method=_required_string(
                    raw_document,
                    "issuing_method",
                    allow_empty=True,
                    max_length=500,
                ),
                issuing_url=_validate_url(issuing_url, index=index),
                submission_format=_required_string(
                    raw_document,
                    "submission_format",
                    allow_empty=True,
                    max_length=100,
                ),
                is_required=_required_bool(raw_document, "is_required"),
                display_order=_required_int(
                    raw_document,
                    "display_order",
                    minimum=0,
                ),
            )
        )
    return documents


def parse_checklist_response(response_text: str) -> list[GeneratedDocument]:
    """Decode and validate a raw Solar checklist response."""

    return validate_checklist_payload(_parse_json_object(response_text))


async def generate_checklist(
    policy: Mapping[str, object],
    *,
    client: SolarClient | None = None,
) -> list[GeneratedDocument]:
    """Generate document rows for review; this function never writes to the DB."""

    messages = build_checklist_messages(policy)
    if client is not None:
        response = await client.complete(messages, temperature=0.0)
        return parse_checklist_response(response)
    async with SolarClient() as solar_client:
        response = await solar_client.complete(messages, temperature=0.0)
        return parse_checklist_response(response)


def _review_directory(review_dir: str | Path | None) -> Path:
    configured = (
        Path(review_dir)
        if review_dir is not None
        else Path(os.getenv("JOOP_REVIEW_DIR", Path.cwd() / "review_drafts"))
    )
    resolved = configured.expanduser().resolve()
    if resolved == Path(resolved.anchor):
        raise ValueError("review directory must not be a filesystem root")
    resolved.mkdir(parents=True, exist_ok=True)
    if not resolved.is_dir():
        raise ValueError("review directory must be a directory")
    return resolved


def _safe_policy_token(policy: Mapping[str, object]) -> str:
    candidate = str(
        policy.get("external_id") or policy.get("id") or policy.get("title") or "policy"
    )
    token = re.sub(r"[^A-Za-z0-9_-]+", "-", candidate).strip("-_")
    return (token or "policy")[:64]


def _write_json_atomically(path: Path, payload: Mapping[str, object]) -> None:
    temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary_path.replace(path)


async def create_checklist_draft(
    policy: Mapping[str, object],
    *,
    review_dir: str | Path | None = None,
    client: SolarClient | None = None,
) -> Path:
    """Generate a pending-review JSON file without touching persistent data."""

    documents = await generate_checklist(policy, client=client)
    draft_id = uuid4().hex
    draft: dict[str, object] = {
        "schema_version": 1,
        "kind": "policy_documents",
        "status": "pending_review",
        "draft_id": draft_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "external_id": policy.get("external_id"),
            "id": policy.get("id"),
            "title": policy.get("title"),
        },
        "documents": [document.to_dict() for document in documents],
    }
    filename = f"documents-{_safe_policy_token(policy)}-{draft_id}.json"
    path = _review_directory(review_dir) / filename
    _write_json_atomically(path, draft)
    return path
