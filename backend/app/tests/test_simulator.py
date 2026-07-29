"""Tests for all category-specific benefit calculators."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.simulator import (
    EmploymentSimulatorRequest,
    FinanceSimulatorRequest,
    HousingSimulatorRequest,
    SimulatorCategory,
    TaxSimulatorRequest,
    TransportSimulatorRequest,
    WelfareSimulatorRequest,
)
from app.services.policy_engine.simulator import (
    calculate_employment,
    calculate_finance,
    calculate_housing,
    calculate_tax,
    calculate_transport,
    calculate_welfare,
)


def test_housing_calculation_excludes_deposit_from_monthly_cost() -> None:
    result = calculate_housing(
        HousingSimulatorRequest(
            monthly_rent_amount=Decimal("500000"),
            monthly_management_fee_amount=Decimal("50000"),
            deposit_amount=Decimal("10000000"),
            monthly_support_amount=Decimal("200000"),
            support_months=6,
        )
    )

    assert result.category is SimulatorCategory.HOUSING
    assert result.monthly_before_amount == Decimal("550000.00")
    assert result.monthly_after_amount == Decimal("350000.00")
    assert result.annual_before_amount == Decimal("6600000.00")
    assert result.annual_after_amount == Decimal("5400000.00")
    assert result.total_benefit_amount == Decimal("1200000.00")


def test_transport_calculation_applies_monthly_cap() -> None:
    result = calculate_transport(
        TransportSimulatorRequest(
            monthly_transport_cost_amount=Decimal("100000"),
            reimbursement_rate_percent=Decimal("20"),
            monthly_support_cap_amount=Decimal("15000"),
            support_months=12,
        )
    )

    assert result.monthly_savings_amount == Decimal("15000.00")
    assert result.monthly_after_amount == Decimal("85000.00")
    assert result.annual_savings_amount == Decimal("180000.00")


def test_finance_calculation_uses_decimal_interest_only_math() -> None:
    result = calculate_finance(
        FinanceSimulatorRequest(
            principal_amount=Decimal("12000000"),
            annual_interest_rate_percent=Decimal("6"),
            interest_reduction_rate_percent=Decimal("2"),
            support_months=12,
        )
    )

    assert result.monthly_before_amount == Decimal("60000.00")
    assert result.monthly_after_amount == Decimal("40000.00")
    assert result.annual_savings_amount == Decimal("240000.00")
    assert result.total_benefit_amount == Decimal("240000.00")


def test_tax_calculation_applies_annual_cap_and_rounds_half_up() -> None:
    result = calculate_tax(
        TaxSimulatorRequest(
            annual_tax_amount=Decimal("1000000"),
            tax_reduction_rate_percent=Decimal("10"),
            max_reduction_amount=Decimal("80000"),
            support_months=12,
        )
    )

    assert result.monthly_before_amount == Decimal("83333.33")
    assert result.monthly_after_amount == Decimal("76666.67")
    assert result.annual_after_amount == Decimal("920000.00")
    assert result.total_benefit_amount == Decimal("80000.00")


def test_employment_calculation_adds_subsidy_to_cash_flow() -> None:
    result = calculate_employment(
        EmploymentSimulatorRequest(
            monthly_income_amount=Decimal("2000000"),
            monthly_subsidy_amount=Decimal("500000"),
            support_months=6,
        )
    )

    assert result.category is SimulatorCategory.EMPLOYMENT
    assert result.monthly_after_amount == Decimal("2500000.00")
    assert result.annual_before_amount == Decimal("24000000.00")
    assert result.annual_after_amount == Decimal("27000000.00")
    assert result.total_benefit_amount == Decimal("3000000.00")


def test_welfare_calculation_never_reduces_cost_below_zero() -> None:
    result = calculate_welfare(
        WelfareSimulatorRequest(
            monthly_living_cost_amount=Decimal("300000"),
            monthly_benefit_amount=Decimal("500000"),
            support_months=12,
        )
    )

    assert result.monthly_after_amount == Decimal("0.00")
    assert result.monthly_savings_amount == Decimal("300000.00")
    assert result.total_benefit_amount == Decimal("3600000.00")


def test_annual_view_is_limited_to_twelve_months_but_total_is_full_term() -> None:
    result = calculate_employment(
        EmploymentSimulatorRequest(
            monthly_income_amount=Decimal("0"),
            monthly_subsidy_amount=Decimal("100000"),
            support_months=18,
        )
    )

    assert result.annual_savings_amount == Decimal("1200000.00")
    assert result.total_benefit_amount == Decimal("1800000.00")


def test_request_rejects_negative_money() -> None:
    with pytest.raises(ValidationError):
        HousingSimulatorRequest(
            monthly_rent_amount=Decimal("-1"),
            monthly_support_amount=Decimal("0"),
        )


@pytest.mark.parametrize(
    "calculator_request",
    [
        HousingSimulatorRequest(
            monthly_rent_amount=0,
            monthly_support_amount=0,
        ),
        TransportSimulatorRequest(
            monthly_transport_cost_amount=0,
            reimbursement_rate_percent=0,
        ),
        FinanceSimulatorRequest(
            principal_amount=0,
            annual_interest_rate_percent=0,
            interest_reduction_rate_percent=0,
        ),
        TaxSimulatorRequest(
            annual_tax_amount=0,
            tax_reduction_rate_percent=0,
        ),
        EmploymentSimulatorRequest(
            monthly_income_amount=0,
            monthly_subsidy_amount=0,
        ),
        WelfareSimulatorRequest(
            monthly_living_cost_amount=0,
            monthly_benefit_amount=0,
        ),
    ],
)
def test_every_request_is_a_transient_dto_with_no_identifier(
    calculator_request: object,
) -> None:
    assert not hasattr(calculator_request, "id")
    assert not hasattr(calculator_request, "user_id")
