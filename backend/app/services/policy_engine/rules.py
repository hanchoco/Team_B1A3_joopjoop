"""Safe, side-effect-free primitives used by the policy matcher.

Only condition keys in :data:`CONDITION_KEY_REGISTRY` may be evaluated.  This
prevents an AI-extracted key from becoming an arbitrary attribute traversal.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from types import MappingProxyType
from typing import Any


class RuleOperator(str, Enum):
    """Operators accepted from structured policy conditions."""

    EQ = "EQ"
    NE = "NE"
    IN = "IN"
    NOT_IN = "NOT_IN"
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    BETWEEN = "BETWEEN"
    CONTAINS = "CONTAINS"
    EXISTS = "EXISTS"
    MANUAL_CHECK = "MANUAL_CHECK"


class ConditionCheckMode(str, Enum):
    """How a policy condition is expected to be confirmed."""

    AUTO = "AUTO"
    MANUAL = "MANUAL"
    DOCUMENT = "DOCUMENT"


class RuleEvaluationError(ValueError):
    """Raised when a structured rule cannot be evaluated safely."""


@dataclass(frozen=True, slots=True)
class ConditionKeySpec:
    """Allowed context paths for one stable condition key."""

    key: str
    context_paths: tuple[str, ...]
    description: str


def _profile_spec(field_name: str, description: str) -> ConditionKeySpec:
    return ConditionKeySpec(
        key=f"profile.{field_name}",
        context_paths=(f"profile.{field_name}", field_name),
        description=description,
    )


def _category_spec(namespace: str, field_name: str, description: str) -> ConditionKeySpec:
    key = f"{namespace}.{field_name}"
    return ConditionKeySpec(
        key=key,
        context_paths=(key, f"category_answers.{key}"),
        description=description,
    )


_CONDITION_SPECS = (
    _profile_spec("age", "기준 연도의 만 나이 대체값(기준 연도 - 출생 연도)"),
    _profile_spec("birth_year", "출생 연도"),
    _profile_spec("region_code", "거주 지역 코드"),
    _profile_spec("region_sido", "시·도"),
    _profile_spec("region_sigungu", "시·군·구"),
    _profile_spec("income_band_code", "소득 구간 코드"),
    _profile_spec("employment_status_code", "취업 상태 코드"),
    _profile_spec("household_type_code", "가구 형태 코드"),
    _profile_spec("household_size", "가구원 수"),
    _profile_spec("housing_type_code", "주거 형태 코드"),
    ConditionKeySpec(
        key="employment.company_size_code",
        context_paths=(
            "employment.company_size_code",
            "category_answers.employment.company_size_code",
        ),
        description="기업 규모",
    ),
    ConditionKeySpec(
        key="employment.contract_type_code",
        context_paths=(
            "employment.contract_type_code",
            "category_answers.employment.contract_type_code",
        ),
        description="근로 계약 형태",
    ),
    ConditionKeySpec(
        key="employment.tenure_months",
        context_paths=(
            "employment.tenure_months",
            "category_answers.employment.tenure_months",
        ),
        description="근속 개월 수",
    ),
    ConditionKeySpec(
        key="employment.insurance_enrolled",
        context_paths=(
            "employment.insurance_enrolled",
            "category_answers.employment.insurance_enrolled",
        ),
        description="고용보험 가입 여부",
    ),
    ConditionKeySpec(
        key="employment.job_field_code",
        context_paths=(
            "employment.job_field_code",
            "category_answers.employment.job_field_code",
        ),
        description="직무 분야",
    ),
    ConditionKeySpec(
        key="housing.has_lease_contract",
        context_paths=(
            "housing.has_lease_contract",
            "category_answers.housing.has_lease_contract",
        ),
        description="임대차 계약 서류 확인 여부",
    ),
    ConditionKeySpec(
        key="housing.deposit_amount",
        context_paths=(
            "housing.deposit_amount",
            "category_answers.housing.deposit_amount",
        ),
        description="임차 보증금",
    ),
    ConditionKeySpec(
        key="housing.monthly_rent_amount",
        context_paths=(
            "housing.monthly_rent_amount",
            "category_answers.housing.monthly_rent_amount",
        ),
        description="월세액",
    ),
    ConditionKeySpec(
        key="housing.is_household_head",
        context_paths=(
            "housing.is_household_head",
            "category_answers.housing.is_household_head",
        ),
        description="세대주 여부",
    ),
    ConditionKeySpec(
        key="housing.residence_months",
        context_paths=(
            "housing.residence_months",
            "category_answers.housing.residence_months",
        ),
        description="현재 거주지 거주 개월 수",
    ),
    ConditionKeySpec(
        key="finance.monthly_income_amount",
        context_paths=(
            "finance.monthly_income_amount",
            "category_answers.finance.monthly_income_amount",
        ),
        description="월 평균 소득",
    ),
    ConditionKeySpec(
        key="finance.annual_income_amount",
        context_paths=(
            "finance.annual_income_amount",
            "category_answers.finance.annual_income_amount",
        ),
        description="연 소득",
    ),
    ConditionKeySpec(
        key="finance.total_asset_amount",
        context_paths=(
            "finance.total_asset_amount",
            "category_answers.finance.total_asset_amount",
        ),
        description="총 자산가액",
    ),
    ConditionKeySpec(
        key="finance.total_debt_amount",
        context_paths=(
            "finance.total_debt_amount",
            "category_answers.finance.total_debt_amount",
        ),
        description="총 부채액",
    ),
    ConditionKeySpec(
        key="finance.fixed_monthly_expense_amount",
        context_paths=(
            "finance.fixed_monthly_expense_amount",
            "category_answers.finance.fixed_monthly_expense_amount",
        ),
        description="월 고정 지출(월세, 대출상환 등)",
    ),
    ConditionKeySpec(
        key="welfare.is_basic_livelihood_recipient",
        context_paths=(
            "welfare.is_basic_livelihood_recipient",
            "category_answers.welfare.is_basic_livelihood_recipient",
        ),
        description="기초생활수급자 여부",
    ),
    ConditionKeySpec(
        key="welfare.is_near_poverty_household",
        context_paths=(
            "welfare.is_near_poverty_household",
            "category_answers.welfare.is_near_poverty_household",
        ),
        description="차상위계층 해당 여부",
    ),
)

CONDITION_KEY_REGISTRY: Mapping[str, ConditionKeySpec] = MappingProxyType(
    {spec.key: spec for spec in _CONDITION_SPECS}
)
SUPPORTED_OPERATORS: frozenset[str] = frozenset(operator.value for operator in RuleOperator)
MISSING_VALUE: Any = object()


def normalise_operator(value: object) -> RuleOperator:
    """Return a supported operator regardless of string/Enum input type."""

    raw_value = value.value if isinstance(value, Enum) else value
    if not isinstance(raw_value, str):
        raise RuleEvaluationError("연산자는 문자열 또는 Enum이어야 합니다.")
    try:
        return RuleOperator(raw_value.strip().upper())
    except ValueError as exc:
        raise RuleEvaluationError(f"지원하지 않는 연산자입니다: {raw_value}") from exc


def normalise_check_mode(value: object | None) -> ConditionCheckMode:
    """Normalise an absent check mode to AUTO."""

    if value is None:
        return ConditionCheckMode.AUTO
    raw_value = value.value if isinstance(value, Enum) else value
    if not isinstance(raw_value, str):
        raise RuleEvaluationError("확인 방식은 문자열 또는 Enum이어야 합니다.")
    try:
        return ConditionCheckMode(raw_value.strip().upper())
    except ValueError as exc:
        raise RuleEvaluationError(f"지원하지 않는 확인 방식입니다: {raw_value}") from exc


def parse_expected_value(raw_value: object) -> object:
    """Parse a JSON-encoded expected value while preserving plain strings."""

    if not isinstance(raw_value, str):
        return raw_value

    stripped = raw_value.strip()
    if not stripped:
        return raw_value
    if stripped[0] not in {"{", "[", '"'} and stripped not in {
        "true",
        "false",
        "null",
    }:
        return raw_value
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise RuleEvaluationError("expected_value_json이 올바른 JSON이 아닙니다.") from exc


def is_registered_condition_key(condition_key: str) -> bool:
    """Return whether a key is explicitly approved for automatic matching."""

    return condition_key in CONDITION_KEY_REGISTRY


def is_missing_value(value: object) -> bool:
    """Detect an unavailable answer without treating zero/False as missing."""

    return value is MISSING_VALUE or value is None or (isinstance(value, str) and not value.strip())


def resolve_condition_value(
    condition_key: str,
    context: Mapping[str, object] | object,
    *,
    reference_date: date | None = None,
) -> object:
    """Resolve one registered key from a mapping or attribute-based context.

    Both nested mappings (``{"profile": {"birth_year": 2000}}``) and flat
    dotted mappings (``{"profile.birth_year": 2000}``) are supported.  ORM
    objects are read through attributes only; this function performs no query.
    """

    spec = CONDITION_KEY_REGISTRY.get(condition_key)
    if spec is None:
        return MISSING_VALUE

    for path in spec.context_paths:
        resolved = _read_path(context, path)
        if not is_missing_value(resolved):
            return resolved

    if condition_key == "profile.age":
        birth_year = resolve_condition_value(
            "profile.birth_year",
            context,
            reference_date=reference_date,
        )
        if is_missing_value(birth_year) or isinstance(birth_year, bool):
            return MISSING_VALUE
        try:
            year = int(birth_year)
        except (TypeError, ValueError):
            return MISSING_VALUE
        current_year = (reference_date or date.today()).year
        if year <= 0 or year > current_year:
            return MISSING_VALUE
        return current_year - year

    return MISSING_VALUE


def evaluate_rule(
    operator: RuleOperator | str | Enum,
    actual_value: object,
    expected_value: object,
    *,
    condition_key: str | None = None,
) -> bool:
    """Evaluate a validated operator against an actual and expected value."""

    normalised_operator = normalise_operator(operator)
    expected = parse_expected_value(expected_value)

    if normalised_operator is RuleOperator.MANUAL_CHECK:
        raise RuleEvaluationError("수동 확인 조건은 자동 판정할 수 없습니다.")

    if normalised_operator is RuleOperator.EXISTS:
        expected_exists = True if expected is None else bool(_scalar(expected))
        return (not is_missing_value(actual_value)) is expected_exists

    if is_missing_value(actual_value):
        raise RuleEvaluationError("실제 값이 없어 자동 판정할 수 없습니다.")

    if normalised_operator is RuleOperator.EQ:
        return _equal(actual_value, _scalar(expected))
    if normalised_operator is RuleOperator.NE:
        return not _equal(actual_value, _scalar(expected))
    if normalised_operator is RuleOperator.IN:
        if condition_key == "profile.region_code":
            return _region_prefix_in(actual_value, _values(expected))
        return any(_equal(actual_value, item) for item in _values(expected))
    if normalised_operator is RuleOperator.NOT_IN:
        if condition_key == "profile.region_code":
            return not _region_prefix_in(actual_value, _values(expected))
        return not any(_equal(actual_value, item) for item in _values(expected))
    if normalised_operator is RuleOperator.GT:
        return _compare(actual_value, _scalar(expected)) > 0
    if normalised_operator is RuleOperator.GTE:
        return _compare(actual_value, _scalar(expected)) >= 0
    if normalised_operator is RuleOperator.LT:
        return _compare(actual_value, _scalar(expected)) < 0
    if normalised_operator is RuleOperator.LTE:
        return _compare(actual_value, _scalar(expected)) <= 0
    if normalised_operator is RuleOperator.BETWEEN:
        minimum, maximum = _range(expected)
        return _compare(actual_value, minimum) >= 0 and _compare(actual_value, maximum) <= 0
    if normalised_operator is RuleOperator.CONTAINS:
        return _contains(actual_value, expected)

    raise RuleEvaluationError(f"구현되지 않은 연산자입니다: {normalised_operator.value}")


def _read_path(source: object, path: str) -> object:
    if isinstance(source, Mapping) and path in source:
        return source[path]

    current = source
    for segment in path.split("."):
        if isinstance(current, Mapping):
            if segment not in current:
                return MISSING_VALUE
            current = current[segment]
            continue
        try:
            current = getattr(current, segment)
        except (AttributeError, TypeError):
            return MISSING_VALUE
    return current


def _scalar(value: object) -> object:
    if isinstance(value, Mapping):
        if "value" in value:
            return value["value"]
        if "expected" in value:
            return value["expected"]
        raise RuleEvaluationError("단일 기대값에는 'value'가 필요합니다.")
    return value


def _values(value: object) -> tuple[object, ...]:
    candidate: object = value
    if isinstance(value, Mapping):
        if "values" in value:
            candidate = value["values"]
        elif "value" in value:
            candidate = value["value"]
        else:
            raise RuleEvaluationError("목록 기대값에는 'values'가 필요합니다.")

    if isinstance(candidate, (str, bytes, bytearray)) or not isinstance(candidate, Sequence):
        raise RuleEvaluationError("IN/NOT_IN 기대값은 목록이어야 합니다.")
    return tuple(candidate)


def _range(value: object) -> tuple[object, object]:
    if isinstance(value, Mapping):
        if "min" not in value or "max" not in value:
            raise RuleEvaluationError("BETWEEN 기대값에는 min과 max가 필요합니다.")
        return value["min"], value["max"]
    if (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray))
        and len(value) == 2
    ):
        return value[0], value[1]
    raise RuleEvaluationError("BETWEEN 기대값은 min/max 또는 길이 2 목록이어야 합니다.")


def _region_prefix_in(actual: object, values: tuple[object, ...]) -> bool:
    """Compare region codes by their leading 2 digits (시/도 단위).

    Policy conditions store fine-grained 시/군/구 codes (5 digits) while user
    profiles only collect the coarser 시/도 code (2 digits), so an exact
    match is never possible. Matching on the shared 시/도 prefix keeps the
    condition meaningful without requiring a full district-level catalog.
    """

    actual_prefix = str(actual).strip()[:2]
    if not actual_prefix:
        return False
    return any(str(item).strip()[:2] == actual_prefix for item in values)


def _equal(left: object, right: object) -> bool:
    left = left.value if isinstance(left, Enum) else left
    right = right.value if isinstance(right, Enum) else right

    if isinstance(left, bool) or isinstance(right, bool):
        return left is right

    if _is_number(left) or _is_number(right):
        try:
            return _decimal(left) == _decimal(right)
        except RuleEvaluationError:
            return False

    if isinstance(left, (date, datetime)) or isinstance(right, (date, datetime)):
        try:
            return _date_value(left) == _date_value(right)
        except RuleEvaluationError:
            return False

    return left == right


def _compare(left: object, right: object) -> int:
    left = left.value if isinstance(left, Enum) else left
    right = right.value if isinstance(right, Enum) else right

    try:
        left_decimal = _decimal(left)
        right_decimal = _decimal(right)
    except RuleEvaluationError:
        try:
            left_date = _date_value(left)
            right_date = _date_value(right)
        except RuleEvaluationError as exc:
            raise RuleEvaluationError("대소 비교 값은 숫자 또는 ISO 날짜여야 합니다.") from exc
        return (left_date > right_date) - (left_date < right_date)
    return (left_decimal > right_decimal) - (left_decimal < right_decimal)


def _contains(actual: object, expected: object) -> bool:
    candidates: tuple[object, ...]
    if isinstance(expected, Mapping) and "values" in expected:
        candidates = _values(expected)
    else:
        candidates = (_scalar(expected),)

    if isinstance(actual, str):
        return all(isinstance(candidate, str) and candidate in actual for candidate in candidates)
    if isinstance(actual, Mapping):
        return all(candidate in actual for candidate in candidates)
    if isinstance(actual, Sequence) and not isinstance(actual, (bytes, bytearray)):
        return all(any(_equal(item, candidate) for item in actual) for candidate in candidates)
    raise RuleEvaluationError("CONTAINS 실제 값은 문자열, 목록 또는 매핑이어야 합니다.")


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)


def _decimal(value: object) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise RuleEvaluationError("Boolean/None은 숫자로 비교할 수 없습니다.")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, AttributeError, ValueError) as exc:
        raise RuleEvaluationError(f"숫자로 변환할 수 없습니다: {value!r}") from exc


def _date_value(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            try:
                parsed_date = date.fromisoformat(value)
            except ValueError as exc:
                raise RuleEvaluationError(f"ISO 날짜로 변환할 수 없습니다: {value!r}") from exc
            return datetime.combine(parsed_date, datetime.min.time())
    raise RuleEvaluationError(f"날짜로 변환할 수 없습니다: {value!r}")
