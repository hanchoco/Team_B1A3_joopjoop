"""Tests for pure condition and policy-card matching."""

from __future__ import annotations

from datetime import date

import pytest

from app.models.user_policy import EligibilityStatus
from app.schemas.policy import ConditionStatus
from app.services.policy_engine.matcher import (
    evaluate_condition,
    evaluate_policy,
)


def _condition(
    *,
    key: str = "profile.household_size",
    operator: str = "EQ",
    expected: object = 1,
    check_mode: str = "AUTO",
    **extra: object,
) -> dict[str, object]:
    return {
        "condition_key": key,
        "operator": operator,
        "expected_value_json": expected,
        "check_mode": check_mode,
        **extra,
    }


@pytest.mark.parametrize(
    ("operator", "actual", "expected"),
    [
        ("EQ", 3, 3),
        ("NE", 3, 4),
        ("IN", "41", {"values": ["11", "41"]}),
        ("NOT_IN", "26", {"values": ["11", "41"]}),
        ("GT", 3, 2),
        ("GTE", 3, 3),
        ("LT", 3, 4),
        ("LTE", 3, 3),
        ("BETWEEN", 3, {"min": 1, "max": 3}),
        ("CONTAINS", ["BACKEND", "AI"], {"values": ["AI"]}),
        ("EXISTS", 3, None),
    ],
)
def test_supported_operators_can_satisfy(
    operator: str,
    actual: object,
    expected: object,
) -> None:
    key = (
        "profile.region_code"
        if operator in {"IN", "NOT_IN"}
        else "employment.job_field" if operator == "CONTAINS" else "profile.household_size"
    )
    context = {key: actual}

    result = evaluate_condition(
        _condition(key=key, operator=operator, expected=expected),
        context,
    )

    assert result.status is ConditionStatus.SATISFIED


def test_json_expected_value_and_derived_age_are_supported() -> None:
    condition = _condition(
        key="profile.age",
        operator="BETWEEN",
        expected='{"min": 19, "max": 34}',
    )

    result = evaluate_condition(
        condition,
        {"profile": {"birth_year": 2000}},
        reference_date=date(2026, 7, 29),
    )

    assert result.status is ConditionStatus.SATISFIED
    assert result.actual_value == 26


@pytest.mark.parametrize(
    "condition",
    [
        _condition(check_mode="MANUAL"),
        _condition(check_mode="DOCUMENT"),
        _condition(operator="MANUAL_CHECK", expected=None),
    ],
)
def test_manual_or_document_conditions_need_review(
    condition: dict[str, object],
) -> None:
    result = evaluate_condition(condition, {"profile": {"household_size": 1}})

    assert result.status is ConditionStatus.NEEDS_REVIEW


def test_missing_context_value_needs_review() -> None:
    result = evaluate_condition(_condition(), {"profile": {}})

    assert result.status is ConditionStatus.NEEDS_REVIEW
    assert result.actual_value is None


def test_false_boolean_is_a_real_value_not_a_missing_answer() -> None:
    result = evaluate_condition(
        _condition(
            key="employment.insurance_enrolled",
            expected=False,
        ),
        {"employment": {"insurance_enrolled": False}},
    )

    assert result.status is ConditionStatus.SATISFIED


def test_unknown_condition_key_needs_review() -> None:
    result = evaluate_condition(
        _condition(key="profile.unapproved_ai_key"),
        {"profile": {"unapproved_ai_key": 1}},
    )

    assert result.status is ConditionStatus.NEEDS_REVIEW


def test_failed_condition_is_unsatisfied_and_uses_failure_message() -> None:
    result = evaluate_condition(
        _condition(expected=2, failure_message="가구원 수 기준을 충족하지 않습니다."),
        {"profile": {"household_size": 1}},
    )

    assert result.status is ConditionStatus.UNSATISFIED
    assert result.reason == "가구원 수 기준을 충족하지 않습니다."


def test_policy_is_likely_only_when_every_condition_is_satisfied() -> None:
    conditions = [
        _condition(key="profile.household_size", expected=1),
        _condition(
            key="profile.employment_status_code",
            operator="IN",
            expected={"values": ["EMPLOYED", "JOB_SEEKER"]},
        ),
    ]
    context = {
        "profile": {
            "household_size": 1,
            "employment_status_code": "EMPLOYED",
        }
    }

    result = evaluate_policy(conditions, context)

    assert result.status is EligibilityStatus.ELIGIBLE
    assert result.satisfied_condition_count == 2
    assert result.total_condition_count == 2


def test_truly_unsatisfied_required_condition_makes_card_ineligible() -> None:
    result = evaluate_policy(
        [
            _condition(key="profile.employment_status_code", expected="EMPLOYED"),
            _condition(key="profile.household_size", expected=2),
        ],
        {"profile": {"employment_status_code": "EMPLOYED", "household_size": 1}},
    )
    assert result.status is EligibilityStatus.INELIGIBLE


def test_manual_check_condition_makes_card_need_review() -> None:
    result = evaluate_policy(
        [
            _condition(key="profile.employment_status_code", expected="EMPLOYED"),
            _condition(key="housing.rental_contract_verified", operator="MANUAL_CHECK",
                       expected=None, check_mode="DOCUMENT"),
        ],
        {"profile": {"employment_status_code": "EMPLOYED", "household_size": 1}},
    )
    assert result.status is EligibilityStatus.NEEDS_REVIEW
    assert result.total_condition_count == 2


def test_alternate_eligibility_paths_use_or_across_groups() -> None:
    """그룹1: 서울거주 AND 재직자 / 그룹2: 서울거주 AND 구직자 — 하나만 맞아도 통과"""
    conditions = [
        _condition(key="profile.region_code", expected="11", condition_group_no=1),
        _condition(key="profile.employment_status_code", expected="EMPLOYED", condition_group_no=1),
        _condition(key="profile.region_code", expected="11", condition_group_no=2),
        _condition(key="profile.employment_status_code", expected="JOB_SEEKER", condition_group_no=2),
    ]
    context = {"profile": {"region_code": "11", "employment_status_code": "JOB_SEEKER"}}

    result = evaluate_policy(conditions, context)

    assert result.status is EligibilityStatus.ELIGIBLE