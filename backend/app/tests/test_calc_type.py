"""Tests for the benefit_type + category -> logical CalcType resolution."""

from __future__ import annotations

import pytest

from app.models.policy import BenefitType, Policy, PolicyBenefit, PolicyCategory
from app.models.user_category_profile import Category, CategoryCode
from app.services.policy_engine.calc_type import CalcType, can_simulate, resolve_calc_type


def _benefit(
    benefit_type: BenefitType | str,
    calculation_rule_json: dict | None = None,
) -> PolicyBenefit:
    return PolicyBenefit(
        benefit_type=benefit_type,
        amount_type="FIXED",
        calculation_rule_json=calculation_rule_json,
    )


def _policy(*category_codes: CategoryCode | str) -> Policy:
    policy = Policy(title="테스트 정책")
    policy.category_links = [
        PolicyCategory(category=Category(code=code, name=str(code))) for code in category_codes
    ]
    return policy


@pytest.mark.parametrize(
    ("benefit_type", "expected"),
    [
        (BenefitType.LOAN, CalcType.LOAN_INTEREST),
        ("LOAN", CalcType.LOAN_INTEREST),
        (BenefitType.SAVINGS, CalcType.SAVINGS_ASSET),
        (BenefitType.TAX_REDUCTION, CalcType.TAX_DEDUCTION),
    ],
)
def test_direct_benefit_type_mapping_ignores_category(
    benefit_type: BenefitType | str,
    expected: CalcType,
) -> None:
    """These benefit types map 1:1 regardless of the policy's categories."""

    policy = _policy(CategoryCode.HOUSING, CategoryCode.EMPLOYMENT)

    assert resolve_calc_type(_benefit(benefit_type), policy) is expected


@pytest.mark.parametrize("benefit_type", [BenefitType.CASH, BenefitType.DISCOUNT])
def test_cash_like_benefit_maps_to_housing_rent_when_policy_has_housing_category(
    benefit_type: BenefitType,
) -> None:
    policy = _policy(CategoryCode.HOUSING)

    assert resolve_calc_type(_benefit(benefit_type), policy) is CalcType.HOUSING_RENT


@pytest.mark.parametrize("benefit_type", [BenefitType.CASH, BenefitType.DISCOUNT])
def test_cash_like_benefit_maps_to_employment_education_when_policy_has_employment_category(
    benefit_type: BenefitType,
) -> None:
    policy = _policy(CategoryCode.EMPLOYMENT)

    assert resolve_calc_type(_benefit(benefit_type), policy) is CalcType.EMPLOYMENT_EDUCATION


def test_housing_category_takes_priority_over_employment_category() -> None:
    """A policy tagged with both HOUSING and EMPLOYMENT resolves to HOUSING_RENT."""

    policy = _policy(CategoryCode.EMPLOYMENT, CategoryCode.HOUSING)

    assert resolve_calc_type(_benefit(BenefitType.CASH), policy) is CalcType.HOUSING_RENT


@pytest.mark.parametrize("benefit_type", [BenefitType.CASH, BenefitType.DISCOUNT])
def test_cash_like_benefit_falls_back_to_cash_voucher_for_other_categories(
    benefit_type: BenefitType,
) -> None:
    policy = _policy(CategoryCode.WELFARE)

    assert resolve_calc_type(_benefit(benefit_type), policy) is CalcType.CASH_VOUCHER


def test_cash_like_benefit_falls_back_to_cash_voucher_with_no_categories() -> None:
    policy = _policy()

    assert resolve_calc_type(_benefit(BenefitType.CASH), policy) is CalcType.CASH_VOUCHER


@pytest.mark.parametrize("benefit_type", [BenefitType.SERVICE, BenefitType.OTHER])
def test_non_simulatable_benefit_types_resolve_to_none(
    benefit_type: BenefitType,
) -> None:
    policy = _policy(CategoryCode.HOUSING)

    assert resolve_calc_type(_benefit(benefit_type), policy) is None


_VALID_LOAN_INTEREST_RULE = {
    "policy_interest_rate_percent": 1.8,
    "max_loan_amount": 200000000,
    "max_support_months": 24,
    "repayment_type": "BULLET",
}

_VALID_CASH_VOUCHER_FIXED_RULE = {
    "amount_type": "FIXED",
    "amount": 300000,
    "payment_cycle": "ONCE",
    "max_count": 1,
}


@pytest.mark.parametrize(
    ("benefit_type", "calculation_rule_json", "expected"),
    [
        (BenefitType.LOAN, _VALID_LOAN_INTEREST_RULE, True),
        (BenefitType.CASH, _VALID_CASH_VOUCHER_FIXED_RULE, True),
        (BenefitType.SERVICE, None, False),
        (BenefitType.OTHER, None, False),
    ],
)
def test_can_simulate_mirrors_resolve_calc_type(
    benefit_type: BenefitType,
    calculation_rule_json: dict | None,
    expected: bool,
) -> None:
    policy = _policy()

    assert can_simulate(_benefit(benefit_type, calculation_rule_json), policy) is expected


@pytest.mark.parametrize(
    ("benefit_type", "calculation_rule_json"),
    [
        (BenefitType.LOAN, None),
        (BenefitType.LOAN, {}),
        (BenefitType.LOAN, {"policy_interest_rate_percent": 1.8}),
        (BenefitType.CASH, None),
        (BenefitType.CASH, {"amount_type": "FIXED"}),
        (BenefitType.CASH, {**_VALID_CASH_VOUCHER_FIXED_RULE, "amount_type": "UNKNOWN"}),
    ],
)
def test_can_simulate_is_false_when_calc_type_resolves_but_rule_json_is_incomplete(
    benefit_type: BenefitType,
    calculation_rule_json: dict | None,
) -> None:
    """A resolvable CalcType is not enough if calculation_rule_json is missing
    the fields simulator.calculate_*() actually reads as required."""

    policy = _policy()

    assert can_simulate(_benefit(benefit_type, calculation_rule_json), policy) is False


@pytest.mark.parametrize(
    "calculation_rule_json",
    [
        {"support_months": 6},
        {"training_allowance_amount": 300000},
        {"education_subsidy_amount": 100000, "support_months": None},
    ],
)
def test_can_simulate_employment_education_accepts_support_months_or_any_amount(
    calculation_rule_json: dict,
) -> None:
    """support_months가 없어도 금액 필드 중 하나만 있으면 1회성 지급으로 계산 가능하다."""

    policy = _policy(CategoryCode.EMPLOYMENT)

    assert can_simulate(_benefit(BenefitType.CASH, calculation_rule_json), policy) is True


def test_can_simulate_employment_education_rejects_when_no_amount_and_no_months() -> None:
    policy = _policy(CategoryCode.EMPLOYMENT)

    assert can_simulate(_benefit(BenefitType.CASH, {}), policy) is False
    assert (
        can_simulate(
            _benefit(
                BenefitType.CASH,
                {
                    "training_allowance_amount": None,
                    "education_subsidy_amount": None,
                    "employment_success_bonus_amount": None,
                    "support_months": None,
                },
            ),
            policy,
        )
        is False
    )
