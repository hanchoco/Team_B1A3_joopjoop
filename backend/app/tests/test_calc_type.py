"""Tests for the benefit_type + category -> logical CalcType resolution."""

from __future__ import annotations

import pytest

from app.models.policy import BenefitType, Policy, PolicyBenefit, PolicyCategory
from app.models.user_category_profile import Category, CategoryCode
from app.services.policy_engine.calc_type import CalcType, can_simulate, resolve_calc_type


def _benefit(benefit_type: BenefitType | str) -> PolicyBenefit:
    return PolicyBenefit(benefit_type=benefit_type, amount_type="FIXED")


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


@pytest.mark.parametrize(
    ("benefit_type", "expected"),
    [
        (BenefitType.LOAN, True),
        (BenefitType.CASH, True),
        (BenefitType.SERVICE, False),
        (BenefitType.OTHER, False),
    ],
)
def test_can_simulate_mirrors_resolve_calc_type(
    benefit_type: BenefitType,
    expected: bool,
) -> None:
    policy = _policy()

    assert can_simulate(_benefit(benefit_type), policy) is expected
