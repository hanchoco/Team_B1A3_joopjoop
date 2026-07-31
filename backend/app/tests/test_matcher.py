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
        ("CONTAINS_ALL", ["BACKEND", "AI"], {"values": ["AI"]}),
        ("CONTAINS_ANY", ["BACKEND"], {"values": ["AI", "BACKEND"]}),
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
        else (
            "employment.job_field_code"
            if operator in {"CONTAINS_ANY", "CONTAINS_ALL"}
            else "profile.household_size"
        )
    )
    context = {key: actual}

    result = evaluate_condition(
        _condition(key=key, operator=operator, expected=expected),
        context,
    )

    assert result.status is ConditionStatus.SATISFIED


def test_region_code_in_matches_by_sido_prefix() -> None:
    """User profiles only store a 2-digit 시/도 code; policy conditions store
    5-digit 시/군/구 codes. IN/NOT_IN must compare by the shared prefix."""

    context = {"profile.region_code": "11"}
    condition = _condition(
        key="profile.region_code",
        operator="IN",
        expected={"values": ["11110", "11140", "41111"]},
    )

    result = evaluate_condition(condition, context)

    assert result.status is ConditionStatus.SATISFIED


def test_region_code_in_does_not_match_other_sido_prefix() -> None:
    context = {"profile.region_code": "26"}
    condition = _condition(
        key="profile.region_code",
        operator="IN",
        expected={"values": ["11110", "11140", "41111"]},
    )

    result = evaluate_condition(condition, context)

    assert result.status is ConditionStatus.UNSATISFIED


def test_other_in_conditions_still_require_exact_match() -> None:
    """The 시/도 prefix rule must stay scoped to profile.region_code only."""

    context = {"profile.income_band_code": "BETWEEN_50_75"}
    condition = _condition(
        key="profile.income_band_code",
        operator="IN",
        expected={"values": ["BELOW_50", "BETWEEN_75_100"]},
    )

    result = evaluate_condition(condition, context)

    assert result.status is ConditionStatus.UNSATISFIED


def test_contains_any_matches_when_only_one_candidate_present() -> None:
    """CONTAINS_ANY is satisfied by a partial match, unlike CONTAINS_ALL."""

    context = {"employment.job_field_code": ["BACKEND"]}
    condition = _condition(
        key="employment.job_field_code",
        operator="CONTAINS_ANY",
        expected={"values": ["AI", "BACKEND"]},
    )

    result = evaluate_condition(condition, context)

    assert result.status is ConditionStatus.SATISFIED


def test_contains_all_requires_every_candidate_present() -> None:
    context = {"employment.job_field_code": ["BACKEND"]}
    condition = _condition(
        key="employment.job_field_code",
        operator="CONTAINS_ALL",
        expected={"values": ["AI", "BACKEND"]},
    )

    result = evaluate_condition(condition, context)

    assert result.status is ConditionStatus.UNSATISFIED


@pytest.mark.parametrize(
    "key",
    [
        "housing.home_ownership_status_code",
        "finance.income_median_ratio",
    ],
)
def test_newly_registered_condition_keys_are_recognised(key: str) -> None:
    context = {key: "SELF" if key.endswith("_code") else 80}
    condition = _condition(key=key, operator="EQ", expected=context[key])

    result = evaluate_condition(condition, context)

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


def test_manual_mode_unregistered_key_shows_manual_reason_not_unregistered_key() -> None:
    """participation_limit is a deliberate sentinel condition_key that is never
    registered for auto-evaluation (it's an informational notice, not a real
    matching field). It must read as a manual-review item, not as if the data
    were broken."""

    result = evaluate_condition(
        _condition(
            key="participation_limit",
            operator="MANUAL_CHECK",
            expected=None,
            check_mode="MANUAL",
        ),
        {"profile": {}},
    )

    assert result.status is ConditionStatus.NEEDS_REVIEW
    assert result.reason == "수동 확인이 필요한 조건입니다."


def test_unknown_key_in_auto_mode_still_flagged_as_unregistered() -> None:
    """A genuinely mistyped/hallucinated key with check_mode AUTO should still
    surface the unregistered-key reason - only MANUAL/DOCUMENT skip it."""

    result = evaluate_condition(
        _condition(key="profile.made_up_key", check_mode="AUTO"),
        {"profile": {"made_up_key": 1}},
    )

    assert result.status is ConditionStatus.NEEDS_REVIEW
    assert "등록되지 않은" in result.reason


def test_failed_condition_is_unsatisfied_and_uses_failure_message() -> None:
    result = evaluate_condition(
        _condition(expected=2, failure_message="가구원 수 기준을 충족하지 않습니다."),
        {"profile": {"household_size": 1}},
    )

    assert result.status is ConditionStatus.UNSATISFIED
    assert result.reason == "가구원 수 기준을 충족하지 않습니다."


def test_failed_condition_with_exception_note_needs_review_instead() -> None:
    result = evaluate_condition(
        _condition(
            expected=2,
            failure_message="가구원 수 기준을 충족하지 않습니다.",
            exception_note="1인 가구도 예외적으로 인정됩니다.",
        ),
        {"profile": {"household_size": 1}},
    )

    assert result.status is ConditionStatus.NEEDS_REVIEW
    assert result.reason == "1인 가구도 예외적으로 인정됩니다."


def test_failed_condition_without_exception_note_keeps_original_behaviour() -> None:
    result = evaluate_condition(
        _condition(
            expected=2,
            failure_message="가구원 수 기준을 충족하지 않습니다.",
            exception_note=None,
        ),
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
            _condition(key="housing.has_lease_contract", operator="MANUAL_CHECK",
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


def test_optional_needs_review_conditions_push_card_to_needs_review() -> None:
    """Regression: is_required=False conditions (income, participation_limit,
    most AI-extracted conditions) used to be skipped entirely from card-level
    aggregation, so a policy with age/region satisfied but five unresolved
    optional conditions still showed as ELIGIBLE. They must now count."""

    conditions = [
        _condition(key="profile.age", operator="BETWEEN", expected={"min": 19, "max": 34}),
        _condition(key="profile.region_code", operator="IN", expected={"values": ["11"]}),
        _condition(
            key="profile.income_band_code",
            operator="IN",
            expected={"values": ["BELOW_50"]},
            is_required=False,
            check_mode="MANUAL",
        ),
        _condition(
            key="participation_limit",
            operator="MANUAL_CHECK",
            expected=None,
            is_required=False,
            check_mode="MANUAL",
        ),
    ]
    context = {"profile": {"age": 25, "region_code": "11"}}

    result = evaluate_policy(conditions, context)

    assert result.status is EligibilityStatus.NEEDS_REVIEW


def test_optional_unsatisfied_condition_without_exception_makes_card_ineligible() -> None:
    """An optional (is_required=False) condition that genuinely fails - and
    has no exception_note - must block the card, not just be ignored."""

    conditions = [
        _condition(key="profile.age", operator="BETWEEN", expected={"min": 19, "max": 34}),
        _condition(key="profile.region_code", operator="IN", expected={"values": ["11"]}),
        _condition(
            key="housing.is_household_head",
            operator="EQ",
            expected=True,
            is_required=False,
            failure_message="세대주만 신청할 수 있습니다.",
        ),
    ]
    context = {
        "profile": {"age": 25, "region_code": "11"},
        "housing": {"is_household_head": False},
    }

    result = evaluate_policy(conditions, context)

    assert result.status is EligibilityStatus.INELIGIBLE


def test_optional_unsatisfied_condition_with_exception_note_stays_needs_review() -> None:
    """The same failing optional condition, but with an exception_note, must
    NOT drag the card down to INELIGIBLE - evaluate_condition() already
    downgraded it to NEEDS_REVIEW, and the card should follow that."""

    conditions = [
        _condition(key="profile.age", operator="BETWEEN", expected={"min": 19, "max": 34}),
        _condition(key="profile.region_code", operator="IN", expected={"values": ["11"]}),
        _condition(
            key="housing.is_household_head",
            operator="EQ",
            expected=True,
            is_required=False,
            failure_message="세대주만 신청할 수 있습니다.",
            exception_note="예외적으로 인정됩니다.",
        ),
    ]
    context = {
        "profile": {"age": 25, "region_code": "11"},
        "housing": {"is_household_head": False},
    }

    result = evaluate_policy(conditions, context)

    assert result.status is EligibilityStatus.NEEDS_REVIEW


def test_finance_monthly_income_condition_matches_category_answer() -> None:
    """`finance.*` keys must resolve from nested category-answer context, the
    same shape `policy_service.build_user_context()` produces."""

    condition = _condition(
        key="finance.monthly_income_amount",
        operator="GTE",
        expected=2000000,
    )
    context = {"finance": {"monthly_income_amount": 2500000}}

    result = evaluate_condition(condition, context)

    assert result.status is ConditionStatus.SATISFIED


def test_housing_has_lease_contract_condition_matches_category_answer() -> None:
    condition = _condition(
        key="housing.has_lease_contract",
        operator="EQ",
        expected=True,
    )
    context = {"housing": {"has_lease_contract": True}}

    result = evaluate_condition(condition, context)

    assert result.status is ConditionStatus.SATISFIED


def test_welfare_condition_key_is_registered() -> None:
    condition = _condition(
        key="welfare.is_basic_livelihood_recipient",
        operator="EQ",
        expected=False,
    )
    context = {"welfare": {"is_basic_livelihood_recipient": True}}

    result = evaluate_condition(condition, context)

    assert result.status is ConditionStatus.UNSATISFIED