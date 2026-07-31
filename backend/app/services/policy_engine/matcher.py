"""Pure policy eligibility matching.

This module accepts already-loaded condition/context objects and never performs
database access.  Both condition-level and policy-level results use the same
three-state vocabulary (``EligibilityStatus``), matched to how each is persisted.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, Protocol

from app.models.user_policy import EligibilityStatus
from app.schemas.policy import ConditionStatus
from app.services.policy_engine.rules import (
    MISSING_VALUE,
    ConditionCheckMode,
    RuleEvaluationError,
    RuleOperator,
    evaluate_rule,
    is_missing_value,
    is_registered_condition_key,
    normalise_check_mode,
    normalise_operator,
    parse_expected_value,
    resolve_condition_value,
)


class ConditionLike(Protocol):
    """Minimal structural contract accepted from a model or DTO."""

    condition_key: str
    operator: str | Enum
    expected_value_json: object
    check_mode: str | Enum
    exception_note: str | None


@dataclass(frozen=True, slots=True)
class ConditionEvaluation:
    """Detailed result for one structured condition."""

    condition_key: str
    status: ConditionStatus
    actual_value: object
    expected_value: object
    reason: str
    condition_id: int | None = None


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    """Aggregated card result and its auditable condition details."""

    status: EligibilityStatus
    condition_results: tuple[ConditionEvaluation, ...]
    satisfied_condition_count: int
    review_condition_count: int
    unsatisfied_condition_count: int
    total_condition_count: int

    @property
    def satisfied_count(self) -> int:
        """Short alias useful to API response mappers."""

        return self.satisfied_condition_count

    @property
    def review_count(self) -> int:
        """Short alias useful to API response mappers."""

        return self.review_condition_count

    @property
    def unsatisfied_count(self) -> int:
        """Short alias useful to API response mappers."""

        return self.unsatisfied_condition_count

    @property
    def total_count(self) -> int:
        """Short alias useful to API response mappers."""

        return self.total_condition_count


def evaluate_condition(
    condition: ConditionLike | Mapping[str, object],
    context: Mapping[str, object] | object,
    *,
    reference_date: date | None = None,
) -> ConditionEvaluation:
    """Evaluate exactly one policy condition.

    Unknown keys, missing user answers, malformed AI output, manual checks, and
    document checks are all conservatively returned as ``NEEDS_REVIEW``.
    """

    condition_id = _optional_int(_field(condition, ("id",), default=None))
    raw_key = _field(condition, ("condition_key",), default=MISSING_VALUE)
    condition_key = raw_key.strip() if isinstance(raw_key, str) else ""
    raw_expected = _field(
        condition,
        ("expected_value_json", "expected_value"),
        default=MISSING_VALUE,
    )

    if not condition_key:
        return _review_result(
            condition_key="",
            expected_value=_safe_expected(raw_expected),
            reason="조건 키가 없어 자동 판정할 수 없습니다.",
            condition_id=condition_id,
        )

    if not is_registered_condition_key(condition_key):
        return _review_result(
            condition_key=condition_key,
            expected_value=_safe_expected(raw_expected),
            reason="등록되지 않은 조건 키이므로 담당자 확인이 필요합니다.",
            condition_id=condition_id,
        )

    raw_check_mode = _field(condition, ("check_mode",), default=None)
    try:
        check_mode = normalise_check_mode(raw_check_mode)
    except (RuleEvaluationError, TypeError, ValueError, ArithmeticError) as exc:
        return _review_result(
            condition_key=condition_key,
            expected_value=_safe_expected(raw_expected),
            reason=str(exc),
            condition_id=condition_id,
        )

    if check_mode in {
        ConditionCheckMode.MANUAL,
        ConditionCheckMode.DOCUMENT,
    }:
        mode_label = "서류" if check_mode is ConditionCheckMode.DOCUMENT else "수동"
        return _review_result(
            condition_key=condition_key,
            expected_value=_safe_expected(raw_expected),
            reason=f"{mode_label} 확인이 필요한 조건입니다.",
            condition_id=condition_id,
        )

    raw_operator = _field(condition, ("operator",), default=MISSING_VALUE)
    try:
        operator = normalise_operator(raw_operator)
    except RuleEvaluationError as exc:
        return _review_result(
            condition_key=condition_key,
            expected_value=_safe_expected(raw_expected),
            reason=str(exc),
            condition_id=condition_id,
        )

    if operator is RuleOperator.MANUAL_CHECK:
        return _review_result(
            condition_key=condition_key,
            expected_value=_safe_expected(raw_expected),
            reason="수동 확인 연산자는 자동 판정하지 않습니다.",
            condition_id=condition_id,
        )

    actual_value = resolve_condition_value(
        condition_key,
        context,
        reference_date=reference_date,
    )
    if is_missing_value(actual_value):
        return _review_result(
            condition_key=condition_key,
            expected_value=_safe_expected(raw_expected),
            reason="사용자 정보가 없어 추가 확인이 필요합니다.",
            condition_id=condition_id,
        )

    if raw_expected is MISSING_VALUE:
        return _review_result(
            condition_key=condition_key,
            expected_value=None,
            reason="기대값이 없어 자동 판정할 수 없습니다.",
            condition_id=condition_id,
            actual_value=actual_value,
        )

    try:
        expected_value = parse_expected_value(raw_expected)
        is_satisfied = evaluate_rule(
            operator,
            actual_value,
            expected_value,
            condition_key=condition_key,
        )
    except (RuleEvaluationError, TypeError, ValueError, ArithmeticError) as exc:
        return _review_result(
            condition_key=condition_key,
            expected_value=_safe_expected(raw_expected),
            reason=str(exc),
            condition_id=condition_id,
            actual_value=actual_value,
        )

    if is_satisfied:
        return ConditionEvaluation(
            condition_key=condition_key,
            status=ConditionStatus.SATISFIED,
            actual_value=actual_value,
            expected_value=expected_value,
            reason="조건을 충족합니다.",
            condition_id=condition_id,
        )

    exception_note = _field(
        condition,
        ("exception_note",),
        default=None,
    )
    if isinstance(exception_note, str) and exception_note.strip():
        return ConditionEvaluation(
            condition_key=condition_key,
            status=ConditionStatus.NEEDS_REVIEW,
            actual_value=actual_value,
            expected_value=expected_value,
            reason=exception_note.strip(),
            condition_id=condition_id,
        )

    failure_message = _field(
        condition,
        ("failure_message",),
        default=None,
    )
    reason = (
        failure_message.strip()
        if isinstance(failure_message, str) and failure_message.strip()
        else "조건을 충족하지 않습니다."
    )
    return ConditionEvaluation(
        condition_key=condition_key,
        status=ConditionStatus.UNSATISFIED,
        actual_value=actual_value,
        expected_value=expected_value,
        reason=reason,
        condition_id=condition_id,
    )


def evaluate_policy(
    conditions: Iterable[ConditionLike | Mapping[str, object]],
    context: Mapping[str, object] | object,
    *,
    reference_date: date | None = None,
) -> PolicyEvaluation:
    condition_list = list(conditions)
    results = tuple(
        evaluate_condition(condition, context, reference_date=reference_date)
        for condition in condition_list
    )
    satisfied_count = sum(r.status is ConditionStatus.SATISFIED for r in results)
    review_count = sum(r.status is ConditionStatus.NEEDS_REVIEW for r in results)
    unsatisfied_count = sum(r.status is ConditionStatus.UNSATISFIED for r in results)

    from collections import defaultdict
    groups: dict[int, list[ConditionStatus]] = defaultdict(list)
    for condition, result in zip(condition_list, results):
        if not _field(condition, ("is_required",), default=True):
            continue  # 선택 조건은 그룹 판정에서 제외 (기존 로직 유지)
        group_no = _field(condition, ("condition_group_no",), default=1)
        groups[group_no].append(result.status)

    if not groups:
        card_status = EligibilityStatus.NEEDS_REVIEW
    else:
        group_statuses = []
        for statuses in groups.values():
            if ConditionStatus.UNSATISFIED in statuses:
                group_statuses.append(EligibilityStatus.INELIGIBLE)
            elif ConditionStatus.NEEDS_REVIEW in statuses:
                group_statuses.append(EligibilityStatus.NEEDS_REVIEW)
            else:
                group_statuses.append(EligibilityStatus.ELIGIBLE)

        # 그룹간 OR: 하나라도 통과하는 그룹이 있으면 전체 통과
        if EligibilityStatus.ELIGIBLE in group_statuses:
            card_status = EligibilityStatus.ELIGIBLE
        elif EligibilityStatus.NEEDS_REVIEW in group_statuses:
            card_status = EligibilityStatus.NEEDS_REVIEW
        else:
            card_status = EligibilityStatus.INELIGIBLE

    return PolicyEvaluation(
        status=card_status,
        condition_results=results,
        satisfied_condition_count=satisfied_count,
        review_condition_count=review_count,
        unsatisfied_condition_count=unsatisfied_count,
        total_condition_count=len(results),
    )

def _review_result(
    *,
    condition_key: str,
    expected_value: object,
    reason: str,
    condition_id: int | None,
    actual_value: object = None,
) -> ConditionEvaluation:
    return ConditionEvaluation(
        condition_key=condition_key,
        status=ConditionStatus.NEEDS_REVIEW,
        actual_value=actual_value,
        expected_value=expected_value,
        reason=reason,
        condition_id=condition_id,
    )


def _safe_expected(raw_expected: object) -> object:
    if raw_expected is MISSING_VALUE:
        return None
    try:
        return parse_expected_value(raw_expected)
    except RuleEvaluationError:
        return raw_expected


def _field(
    condition: ConditionLike | Mapping[str, object],
    names: tuple[str, ...],
    *,
    default: Any,
) -> object:
    for name in names:
        if isinstance(condition, Mapping):
            if name in condition:
                return condition[name]
            continue
        try:
            return getattr(condition, name)
        except (AttributeError, TypeError):
            continue
    return default


def _optional_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
