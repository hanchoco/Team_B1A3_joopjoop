"""Tests for the CalcType-based benefit calculators and simulate() dispatcher."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.policy import BenefitType, Policy, PolicyBenefit, PolicyCategory
from app.models.user_category_profile import Category, CategoryCode
from app.services.policy_engine.calc_type import CalcType
from app.services.policy_engine.simulator import (
    CALC_TYPE_DISCLAIMER,
    CALCULATORS,
    UnsupportedCalcTypeError,
    calculate_cash_voucher,
    calculate_employment_education,
    calculate_housing_rent,
    calculate_loan_interest,
    calculate_savings_asset,
    calculate_tax_deduction,
    simulate,
)


def _benefit(benefit_type: BenefitType | str, calculation_rule_json: dict) -> PolicyBenefit:
    return PolicyBenefit(
        benefit_type=benefit_type,
        amount_type="FORMULA",
        calculation_rule_json=calculation_rule_json,
    )


def _policy(*category_codes: CategoryCode) -> Policy:
    policy = Policy(title="테스트 정책")
    policy.category_links = [
        PolicyCategory(category=Category(code=code, name=str(code))) for code in category_codes
    ]
    return policy


# ---------------------------------------------------------------------------
# calculate_loan_interest
# ---------------------------------------------------------------------------


def test_loan_interest_derives_baseline_rate_from_reduction_rate() -> None:
    rule = {
        "policy_interest_rate_percent": "1.8",
        "interest_reduction_rate_percent": "2.2",
        "max_loan_amount": "200000000",
        "max_support_months": 24,
        "repayment_type": "BULLET",
    }
    result = calculate_loan_interest(rule, {"loan_amount": "100000000"})

    assert result.monthly_before_amount == Decimal("333333.33")
    assert result.monthly_after_amount == Decimal("150000.00")
    assert result.monthly_savings_amount == Decimal("183333.33")
    assert result.annual_savings_amount == Decimal("2200000.00")
    assert result.total_benefit_amount == Decimal("4400000.00")
    assert result.support_months == 24
    assert result.disclaimer == CALC_TYPE_DISCLAIMER


def test_loan_interest_clamps_amount_and_months_to_policy_limits() -> None:
    rule = {
        "policy_interest_rate_percent": "1.8",
        "max_loan_amount": "50000000",
        "max_support_months": 12,
        "repayment_type": "EQUAL_PRINCIPAL_INTEREST",
    }
    result = calculate_loan_interest(
        rule,
        {
            "loan_amount": "80000000",
            "general_interest_rate_percent": "5.0",
            "support_months": 20,
        },
    )

    assert result.monthly_after_amount == Decimal("75000.00")
    assert result.support_months == 12
    assert result.breakdown["loan_amount"] == Decimal("50000000.00")


def test_loan_interest_requires_a_baseline_rate() -> None:
    rule = {
        "policy_interest_rate_percent": "1.8",
        "max_loan_amount": "50000000",
        "max_support_months": 12,
        "repayment_type": "BULLET",
    }
    with pytest.raises(ValueError, match="일반 대출 금리"):
        calculate_loan_interest(rule, {"loan_amount": "10000000"})


def test_loan_interest_missing_required_rule_field_raises() -> None:
    rule = {"max_loan_amount": "50000000", "max_support_months": 12, "repayment_type": "BULLET"}
    with pytest.raises(ValueError, match="calculation_rule_json"):
        calculate_loan_interest(rule, {"loan_amount": "10000000"})


def test_loan_interest_non_numeric_user_input_raises_value_error_not_decimal_error() -> None:
    rule = {
        "policy_interest_rate_percent": "1.8",
        "interest_reduction_rate_percent": "2.2",
        "max_loan_amount": "200000000",
        "max_support_months": 24,
        "repayment_type": "BULLET",
    }
    with pytest.raises(ValueError, match="숫자로 변환할 수 없습니다"):
        calculate_loan_interest(rule, {"loan_amount": "이억원"})


# ---------------------------------------------------------------------------
# calculate_savings_asset
# ---------------------------------------------------------------------------


def test_savings_asset_matches_only_up_to_monthly_cap() -> None:
    rule = {
        "government_match_rate_percent": "100",
        "monthly_max_support_amount": "100000",
        "maturity_months": 36,
        "base_interest_rate_percent": "4.5",
        "bonus_interest_rate_percent": "1.0",
    }
    result = calculate_savings_asset(rule, {"monthly_deposit_amount": "150000"})

    assert result.monthly_before_amount == Decimal("150000.00")
    assert result.monthly_after_amount == Decimal("250000.00")
    assert result.monthly_savings_amount == Decimal("100000.00")
    assert result.annual_after_amount == Decimal("3000000.00")
    assert result.total_benefit_amount == Decimal("3600000.00")
    assert result.support_months == 36
    assert result.breakdown["applied_interest_rate_percent"] == Decimal("5.5000")


def test_savings_asset_missing_required_rule_field_raises() -> None:
    rule = {
        "government_match_rate_percent": "100",
        "monthly_max_support_amount": "100000",
        "maturity_months": 36,
    }
    with pytest.raises(ValueError, match="calculation_rule_json"):
        calculate_savings_asset(rule, {"monthly_deposit_amount": "150000"})


# ---------------------------------------------------------------------------
# calculate_cash_voucher
# ---------------------------------------------------------------------------


def test_cash_voucher_fixed_defaults_count_to_max_count() -> None:
    rule = {"amount_type": "FIXED", "amount": "300000", "payment_cycle": "ONCE", "max_count": 1}
    result = calculate_cash_voucher(rule, {})

    assert result.total_benefit_amount == Decimal("300000.00")
    assert result.support_months == 1


def test_cash_voucher_fixed_monthly_multiplies_by_requested_count() -> None:
    rule = {"amount_type": "FIXED", "amount": "50000", "payment_cycle": "MONTHLY", "max_count": 12}
    result = calculate_cash_voucher(rule, {"count": 3})

    assert result.support_months == 3
    assert result.monthly_after_amount == Decimal("50000.00")
    assert result.total_benefit_amount == Decimal("150000.00")


def test_cash_voucher_percentage_applies_rate_and_cap() -> None:
    rule = {
        "amount_type": "PERCENTAGE",
        "rate_percent": "50",
        "cap_amount": "100000",
        "payment_cycle": "MONTHLY",
    }
    result = calculate_cash_voucher(rule, {"base_amount": "300000", "count": 2})

    assert result.breakdown["applied_benefit_per_payment"] == Decimal("100000.00")
    assert result.support_months == 2
    assert result.total_benefit_amount == Decimal("200000.00")


def test_cash_voucher_rejects_unknown_amount_type() -> None:
    rule = {"amount_type": "WEIRD", "payment_cycle": "ONCE"}
    with pytest.raises(ValueError, match="FIXED 또는 PERCENTAGE"):
        calculate_cash_voucher(rule, {})


# ---------------------------------------------------------------------------
# calculate_housing_rent
# ---------------------------------------------------------------------------


def test_housing_rent_caps_support_by_rent_limit_and_support_cap() -> None:
    rule = {
        "monthly_support_cap_amount": "200000",
        "support_months": 12,
        "deposit_limit_amount": "50000000",
        "rent_limit_amount": "600000",
    }
    result = calculate_housing_rent(
        rule,
        {
            "monthly_rent_amount": "700000",
            "monthly_management_fee_amount": "50000",
            "deposit_amount": "40000000",
        },
    )

    assert result.monthly_before_amount == Decimal("700000.00")
    assert result.monthly_after_amount == Decimal("500000.00")
    assert result.total_benefit_amount == Decimal("2400000.00")
    assert result.breakdown["monthly_management_fee_amount"] == Decimal("50000.00")


def test_housing_rent_support_months_clamped_to_policy_maximum() -> None:
    rule = {"monthly_support_cap_amount": "200000", "support_months": 12}
    result = calculate_housing_rent(
        rule,
        {"monthly_rent_amount": "300000", "support_months": 18},
    )

    assert result.support_months == 12


# ---------------------------------------------------------------------------
# calculate_employment_education
# ---------------------------------------------------------------------------


def test_employment_education_adds_one_time_bonus_to_total_only() -> None:
    rule = {
        "training_allowance_amount": "300000",
        "education_subsidy_amount": "1000000",
        "employment_success_bonus_amount": "1500000",
        "support_months": 6,
    }
    result = calculate_employment_education(rule, {"current_monthly_income_amount": "2000000"})

    assert result.monthly_after_amount == Decimal("3300000.00")
    assert result.annual_savings_amount == Decimal("7800000.00")
    # 훈련수당+교육비만 월/연 환산에 반영: 1300000*6=7800000, 취업성공수당 1500000은 총액에만 가산
    assert result.total_benefit_amount == Decimal("9300000.00")


def test_employment_education_without_bonus_leaves_total_unmodified() -> None:
    rule = {"training_allowance_amount": "300000", "support_months": 6}
    result = calculate_employment_education(rule, {})

    assert result.total_benefit_amount == Decimal("1800000.00")


def test_employment_education_defaults_support_months_to_one_when_absent() -> None:
    """지원 개월 정보가 없는 1회성 실비 지원(예: 자격증 응시료 지원)은 1개월로 계산한다."""

    rule = {"training_allowance_amount": "100000"}
    result = calculate_employment_education(rule, {})

    assert result.support_months == 1
    assert result.monthly_after_amount == Decimal("100000.00")
    assert result.annual_savings_amount == Decimal("100000.00")
    assert result.total_benefit_amount == Decimal("100000.00")


# ---------------------------------------------------------------------------
# calculate_tax_deduction
# ---------------------------------------------------------------------------


def test_tax_deduction_applies_rate_and_caps_at_max_deduction() -> None:
    rule = {
        "deduction_rate_percent": "15",
        "max_deduction_amount": "3000000",
        "deduction_type": "TAX_CREDIT",
    }
    result = calculate_tax_deduction(rule, {"annual_tax_amount": "25000000"})

    assert result.annual_savings_amount == Decimal("3000000.00")
    assert result.support_months == 12
    assert result.breakdown["applied_annual_reduction_amount"] == Decimal("3000000.00")


def test_tax_deduction_rejects_unknown_deduction_type() -> None:
    rule = {"deduction_rate_percent": "15", "deduction_type": "WEIRD"}
    with pytest.raises(ValueError, match="TAX_CREDIT 또는 INCOME_DEDUCTION"):
        calculate_tax_deduction(rule, {"annual_tax_amount": "10000000"})


# ---------------------------------------------------------------------------
# CALCULATORS registry + simulate() dispatcher
# ---------------------------------------------------------------------------


def test_calculators_registry_covers_every_calc_type() -> None:
    assert set(CALCULATORS.keys()) == set(CalcType)


def test_simulate_dispatches_to_loan_interest_for_loan_benefit() -> None:
    rule = {
        "policy_interest_rate_percent": "1.8",
        "interest_reduction_rate_percent": "2.2",
        "max_loan_amount": "200000000",
        "max_support_months": 24,
        "repayment_type": "BULLET",
    }
    benefit = _benefit(BenefitType.LOAN, rule)
    policy = _policy()

    result = simulate(benefit, policy, {"loan_amount": "100000000"})

    assert result.total_benefit_amount == Decimal("4400000.00")


def test_simulate_dispatches_to_housing_rent_for_cash_benefit_with_housing_category() -> None:
    rule = {"monthly_support_cap_amount": "200000", "support_months": 12}
    benefit = _benefit(BenefitType.CASH, rule)
    policy = _policy(CategoryCode.HOUSING)

    result = simulate(benefit, policy, {"monthly_rent_amount": "300000"})

    assert result.total_benefit_amount == Decimal("2400000.00")


def test_simulate_raises_for_unsupported_benefit_type() -> None:
    benefit = _benefit(BenefitType.SERVICE, {})
    policy = _policy()

    with pytest.raises(UnsupportedCalcTypeError):
        simulate(benefit, policy, {})
