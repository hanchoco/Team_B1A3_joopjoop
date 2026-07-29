"""Validated policy-condition extraction with review-only draft output.

This module deliberately has no database dependency. AI output must be written
to and reviewed as a draft before a CRUD layer can persist it.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .prompt_templates import build_rule_extraction_messages
from .solar_client import SolarClient

ALLOWED_OPERATORS = frozenset(
    {
        "EQ",
        "NE",
        "IN",
        "NOT_IN",
        "GT",
        "GTE",
        "LT",
        "LTE",
        "BETWEEN",
        "CONTAINS",
        "EXISTS",
        "MANUAL_CHECK",
    }
)
ALLOWED_CHECK_MODES = frozenset({"AUTO", "MANUAL", "DOCUMENT"})
AUTO_CONDITION_KEYS = frozenset(
    {
        "profile.age",
        "profile.birth_year",
        "profile.region_code",
        "profile.region_sido",
        "profile.region_sigungu",
        "profile.income_band_code",
        "profile.employment_status_code",
        "profile.household_type_code",
        "profile.household_size",
        "profile.housing_type_code",
        "profile.monthly_income_amount",
        "profile.monthly_fixed_expense_amount",
        "employment.company_size",
        "employment.contract_type",
        "employment.tenure_months",
        "employment.insurance_enrolled",
        "employment.job_field",
        "housing.rental_contract_verified",
    }
)
_CONDITION_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")
_MAX_RESPONSE_CHARACTERS = 1_000_000


class ConditionValidationError(ValueError):
    """Raised when generated condition JSON does not match the review schema."""


@dataclass(frozen=True, slots=True)
class ExtractedCondition:
    """One validated draft row for ``PolicyCondition``."""

    condition_key: str
    operator: str
    expected_value_json: object
    condition_group_no: int
    is_required: bool
    check_mode: str
    description: str
    failure_message: str
    sort_order: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) < 3 or not lines[-1].strip().startswith("```"):
        raise ConditionValidationError("unterminated JSON code fence")
    return "\n".join(lines[1:-1]).strip()


def _parse_json_object(text: str) -> Mapping[str, object]:
    if not text.strip():
        raise ConditionValidationError("AI response is empty")
    if len(text) > _MAX_RESPONSE_CHARACTERS:
        raise ConditionValidationError("AI response is too large")
    try:
        payload = json.loads(_strip_json_fence(text))
    except json.JSONDecodeError as exc:
        raise ConditionValidationError("AI response is not valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise ConditionValidationError("AI response must be a JSON object")
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
        raise ConditionValidationError(f"{key} must be a string")
    normalized = value.strip()
    if not allow_empty and not normalized:
        raise ConditionValidationError(f"{key} must not be empty")
    if max_length is not None and len(normalized) > max_length:
        raise ConditionValidationError(f"{key} must be at most {max_length} characters")
    return normalized


def _required_int(
    item: Mapping[str, object],
    key: str,
    *,
    minimum: int,
) -> int:
    value = item.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConditionValidationError(f"{key} must be an integer")
    if value < minimum:
        raise ConditionValidationError(f"{key} must be at least {minimum}")
    return value


def _required_bool(item: Mapping[str, object], key: str) -> bool:
    value = item.get(key)
    if not isinstance(value, bool):
        raise ConditionValidationError(f"{key} must be a boolean")
    return value


def _validate_json_value(value: object) -> object:
    try:
        serialized = json.dumps(value, ensure_ascii=False, allow_nan=False)
        return json.loads(serialized)
    except (TypeError, ValueError) as exc:
        raise ConditionValidationError("expected_value_json must be a valid JSON value") from exc


def _validate_operator_value(
    operator: str,
    value: object,
    *,
    index: int,
) -> None:
    candidate = value
    if isinstance(value, Mapping):
        if operator in {"IN", "NOT_IN", "CONTAINS"} and "values" in value:
            candidate = value["values"]
        elif operator in {"IN", "NOT_IN"} and "value" in value:
            candidate = value["value"]
    if operator in {"IN", "NOT_IN"} and (
        not isinstance(candidate, Sequence) or isinstance(candidate, (str, bytes, bytearray))
    ):
        raise ConditionValidationError(f"conditions[{index}] {operator} requires an array")
    if operator == "BETWEEN":
        has_mapping_range = isinstance(value, Mapping) and "min" in value and "max" in value
        has_sequence_range = (
            isinstance(value, Sequence)
            and not isinstance(value, (str, bytes, bytearray))
            and len(value) == 2
        )
        if not has_mapping_range and not has_sequence_range:
            raise ConditionValidationError(f"conditions[{index}] BETWEEN requires min/max")
    if operator == "EXISTS" and value is not None and not isinstance(value, bool):
        raise ConditionValidationError(f"conditions[{index}] EXISTS expects boolean or null")


def validate_condition_payload(payload: object) -> list[ExtractedCondition]:
    """Validate a decoded ``{"conditions": [...]}`` payload."""

    if not isinstance(payload, Mapping):
        raise ConditionValidationError("condition payload must be an object")
    raw_conditions = payload.get("conditions")
    if not isinstance(raw_conditions, Sequence) or isinstance(
        raw_conditions, (str, bytes, bytearray)
    ):
        raise ConditionValidationError("conditions must be an array")

    conditions: list[ExtractedCondition] = []
    seen: set[tuple[int, str, str]] = set()
    for index, raw_condition in enumerate(raw_conditions):
        if not isinstance(raw_condition, Mapping):
            raise ConditionValidationError(f"conditions[{index}] must be an object")
        condition_key = _required_string(raw_condition, "condition_key")
        if len(condition_key) > 100 or not _CONDITION_KEY_PATTERN.fullmatch(condition_key):
            raise ConditionValidationError(f"conditions[{index}].condition_key is invalid")
        operator = _required_string(raw_condition, "operator").upper()
        if operator not in ALLOWED_OPERATORS:
            raise ConditionValidationError(f"conditions[{index}].operator is unsupported")
        check_mode = _required_string(raw_condition, "check_mode").upper()
        if check_mode not in ALLOWED_CHECK_MODES:
            raise ConditionValidationError(f"conditions[{index}].check_mode is unsupported")
        if (
            check_mode == "AUTO"
            and operator != "MANUAL_CHECK"
            and condition_key not in AUTO_CONDITION_KEYS
        ):
            raise ConditionValidationError(
                f"conditions[{index}].condition_key is not auto-evaluable"
            )
        if operator == "MANUAL_CHECK" and check_mode == "AUTO":
            raise ConditionValidationError(
                f"conditions[{index}] manual operator requires manual check_mode"
            )
        if "expected_value_json" not in raw_condition:
            raise ConditionValidationError(f"conditions[{index}].expected_value_json is required")
        expected_value = _validate_json_value(raw_condition["expected_value_json"])
        _validate_operator_value(operator, expected_value, index=index)
        condition_group_no = _required_int(
            raw_condition,
            "condition_group_no",
            minimum=1,
        )
        identity = (condition_group_no, condition_key, operator)
        if identity in seen:
            raise ConditionValidationError(f"conditions[{index}] duplicates a prior condition")
        seen.add(identity)
        conditions.append(
            ExtractedCondition(
                condition_key=condition_key,
                operator=operator,
                expected_value_json=expected_value,
                condition_group_no=condition_group_no,
                is_required=_required_bool(raw_condition, "is_required"),
                check_mode=check_mode,
                description=_required_string(
                    raw_condition,
                    "description",
                    max_length=500,
                ),
                failure_message=_required_string(
                    raw_condition,
                    "failure_message",
                    allow_empty=True,
                    max_length=500,
                ),
                sort_order=_required_int(
                    raw_condition,
                    "sort_order",
                    minimum=0,
                ),
            )
        )
    return conditions


def parse_condition_response(response_text: str) -> list[ExtractedCondition]:
    """Decode and validate a raw Solar extraction response."""

    return validate_condition_payload(_parse_json_object(response_text))


async def extract_conditions(
    policy: Mapping[str, object],
    *,
    client: SolarClient | None = None,
) -> list[ExtractedCondition]:
    """Extract conditions for review; this function never writes to the DB."""

    messages = build_rule_extraction_messages(policy)
    if client is not None:
        response = await client.complete(messages, temperature=0.0)
        return parse_condition_response(response)
    async with SolarClient() as solar_client:
        response = await solar_client.complete(messages, temperature=0.0)
        return parse_condition_response(response)


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


async def create_condition_draft(
    policy: Mapping[str, object],
    *,
    review_dir: str | Path | None = None,
    client: SolarClient | None = None,
) -> Path:
    """Generate a pending-review JSON file without touching persistent data."""

    conditions = await extract_conditions(policy, client=client)
    draft_id = uuid4().hex
    draft: dict[str, object] = {
        "schema_version": 1,
        "kind": "policy_conditions",
        "status": "pending_review",
        "draft_id": draft_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "external_id": policy.get("external_id"),
            "id": policy.get("id"),
            "title": policy.get("title"),
        },
        "conditions": [condition.to_dict() for condition in conditions],
    }
    filename = f"conditions-{_safe_policy_token(policy)}-{draft_id}.json"
    path = _review_directory(review_dir) / filename
    _write_json_atomically(path, draft)
    return path
