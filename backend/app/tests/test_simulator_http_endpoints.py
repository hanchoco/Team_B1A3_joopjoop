"""HTTP-level coverage for every category-specific simulator endpoint."""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

TOP_LEVEL_RESULT_KEYS = {
    "category",
    "monthly_before_amount",
    "monthly_after_amount",
    "monthly_savings_amount",
    "annual_before_amount",
    "annual_after_amount",
    "annual_savings_amount",
    "total_benefit_amount",
    "support_months",
    "breakdown",
    "disclaimer",
}


def _decimal_map(values: dict[str, object]) -> dict[str, Decimal]:
    return {key: Decimal(str(value)) for key, value in values.items()}


@pytest.mark.parametrize(
    (
        "path",
        "payload",
        "expected_category",
        "expected_amounts",
        "expected_breakdown",
    ),
    [
        pytest.param(
            "/api/v1/simulator/housing",
            {
                "monthly_rent_amount": "500000",
                "monthly_management_fee_amount": "100000",
                "deposit_amount": "10000000",
                "monthly_support_amount": "200000",
                "support_months": 12,
            },
            "HOUSING",
            {
                "monthly_before_amount": Decimal("600000.00"),
                "monthly_after_amount": Decimal("400000.00"),
                "monthly_savings_amount": Decimal("200000.00"),
                "annual_before_amount": Decimal("7200000.00"),
                "annual_after_amount": Decimal("4800000.00"),
                "annual_savings_amount": Decimal("2400000.00"),
                "total_benefit_amount": Decimal("2400000.00"),
            },
            {
                "monthly_rent_amount": Decimal("500000.00"),
                "monthly_management_fee_amount": Decimal("100000.00"),
                "deposit_amount": Decimal("10000000.00"),
                "applied_monthly_support_amount": Decimal("200000.00"),
            },
            id="housing",
        ),
        pytest.param(
            "/api/v1/simulator/transport",
            {
                "monthly_transport_cost_amount": "100000",
                "reimbursement_rate_percent": "20",
                "monthly_support_cap_amount": "15000",
                "support_months": 12,
            },
            "TRANSPORT",
            {
                "monthly_before_amount": Decimal("100000.00"),
                "monthly_after_amount": Decimal("85000.00"),
                "monthly_savings_amount": Decimal("15000.00"),
                "annual_before_amount": Decimal("1200000.00"),
                "annual_after_amount": Decimal("1020000.00"),
                "annual_savings_amount": Decimal("180000.00"),
                "total_benefit_amount": Decimal("180000.00"),
            },
            {
                "monthly_transport_cost_amount": Decimal("100000.00"),
                "reimbursement_rate_percent": Decimal("20.0000"),
                "applied_monthly_support_amount": Decimal("15000.00"),
                "monthly_support_cap_amount": Decimal("15000.00"),
            },
            id="transport",
        ),
        pytest.param(
            "/api/v1/simulator/finance",
            {
                "principal_amount": "12000000",
                "annual_interest_rate_percent": "6",
                "interest_reduction_rate_percent": "2",
                "support_months": 12,
            },
            "FINANCE",
            {
                "monthly_before_amount": Decimal("60000.00"),
                "monthly_after_amount": Decimal("40000.00"),
                "monthly_savings_amount": Decimal("20000.00"),
                "annual_before_amount": Decimal("720000.00"),
                "annual_after_amount": Decimal("480000.00"),
                "annual_savings_amount": Decimal("240000.00"),
                "total_benefit_amount": Decimal("240000.00"),
            },
            {
                "principal_amount": Decimal("12000000.00"),
                "annual_interest_rate_percent": Decimal("6.0000"),
                "applied_interest_reduction_rate_percent": Decimal("2.0000"),
                "supported_annual_interest_rate_percent": Decimal("4.0000"),
            },
            id="finance",
        ),
        pytest.param(
            "/api/v1/simulator/tax",
            {
                "annual_tax_amount": "1000000",
                "tax_reduction_rate_percent": "10",
                "max_reduction_amount": "80000",
                "support_months": 12,
            },
            "TAX",
            {
                "monthly_before_amount": Decimal("83333.33"),
                "monthly_after_amount": Decimal("76666.67"),
                "monthly_savings_amount": Decimal("6666.67"),
                "annual_before_amount": Decimal("1000000.00"),
                "annual_after_amount": Decimal("920000.00"),
                "annual_savings_amount": Decimal("80000.00"),
                "total_benefit_amount": Decimal("80000.00"),
            },
            {
                "annual_tax_amount": Decimal("1000000.00"),
                "tax_reduction_rate_percent": Decimal("10.0000"),
                "applied_annual_reduction_amount": Decimal("80000.00"),
                "max_reduction_amount": Decimal("80000.00"),
            },
            id="tax",
        ),
        pytest.param(
            "/api/v1/simulator/employment",
            {
                "monthly_income_amount": "2000000",
                "monthly_subsidy_amount": "500000",
                "support_months": 6,
            },
            "EMPLOYMENT",
            {
                "monthly_before_amount": Decimal("2000000.00"),
                "monthly_after_amount": Decimal("2500000.00"),
                "monthly_savings_amount": Decimal("500000.00"),
                "annual_before_amount": Decimal("24000000.00"),
                "annual_after_amount": Decimal("27000000.00"),
                "annual_savings_amount": Decimal("3000000.00"),
                "total_benefit_amount": Decimal("3000000.00"),
            },
            {
                "monthly_income_amount": Decimal("2000000.00"),
                "monthly_subsidy_amount": Decimal("500000.00"),
            },
            id="employment",
        ),
        pytest.param(
            "/api/v1/simulator/welfare",
            {
                "monthly_living_cost_amount": "300000",
                "monthly_benefit_amount": "500000",
                "support_months": 12,
            },
            "WELFARE",
            {
                "monthly_before_amount": Decimal("300000.00"),
                "monthly_after_amount": Decimal("0.00"),
                "monthly_savings_amount": Decimal("300000.00"),
                "annual_before_amount": Decimal("3600000.00"),
                "annual_after_amount": Decimal("0.00"),
                "annual_savings_amount": Decimal("3600000.00"),
                "total_benefit_amount": Decimal("3600000.00"),
            },
            {
                "monthly_living_cost_amount": Decimal("300000.00"),
                "requested_monthly_benefit_amount": Decimal("500000.00"),
                "applied_monthly_benefit_amount": Decimal("300000.00"),
            },
            id="welfare",
        ),
    ],
)
def test_all_simulator_http_endpoints_return_exact_results(
    client: TestClient,
    path: str,
    payload: dict[str, object],
    expected_category: str,
    expected_amounts: dict[str, Decimal],
    expected_breakdown: dict[str, Decimal],
) -> None:
    """Every simulator is public, strict, and returns the normalised result."""

    response = client.post(path, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == TOP_LEVEL_RESULT_KEYS
    assert body["category"] == expected_category
    assert body["support_months"] == payload["support_months"]
    assert isinstance(body["disclaimer"], str)
    assert body["disclaimer"].strip()
    for key, expected in expected_amounts.items():
        assert Decimal(str(body[key])) == expected
    assert set(body["breakdown"]) == set(expected_breakdown)
    assert _decimal_map(body["breakdown"]) == expected_breakdown


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        (
            "/api/v1/simulator/housing",
            {
                "monthly_rent_amount": "-1",
                "monthly_support_amount": "0",
            },
        ),
        (
            "/api/v1/simulator/transport",
            {
                "monthly_transport_cost_amount": "10000",
                "reimbursement_rate_percent": "101",
            },
        ),
        (
            "/api/v1/simulator/finance",
            {
                "principal_amount": "1000000",
                "annual_interest_rate_percent": "5",
                "interest_reduction_rate_percent": "1",
                "support_months": 121,
            },
        ),
        (
            "/api/v1/simulator/tax",
            {
                "annual_tax_amount": "100000",
                "tax_reduction_rate_percent": "10",
                "unexpected": "not allowed",
            },
        ),
    ],
)
def test_simulator_http_validation_rejects_invalid_payloads(
    client: TestClient,
    path: str,
    payload: dict[str, object],
) -> None:
    response = client.post(path, json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]
