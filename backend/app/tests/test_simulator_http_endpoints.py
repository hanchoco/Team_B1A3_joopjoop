"""HTTP-level coverage for POST /policies/{policy_id}/benefits/{benefit_id}/simulate."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.policy import Policy, PolicyBenefit, PolicyCategory
from app.models.user_category_profile import Category

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


def _authenticated_headers(client: TestClient, *, email: str) -> dict[str, str]:
    signup = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": "safe-password-123",
            "nickname": "시뮬레이터테스터",
            "consents": [
                {
                    "consent_type": "TERMS_REQUIRED",
                    "consent_version": "1.0",
                    "is_agreed": True,
                },
                {
                    "consent_type": "PRIVACY_REQUIRED",
                    "consent_version": "1.0",
                    "is_agreed": True,
                },
            ],
        },
    )
    assert signup.status_code == 201, signup.text
    token = signup.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_policy_with_benefit(
    *,
    external_id: str,
    benefit_type: str,
    amount_type: str,
    calculation_rule_json: dict[str, object] | None,
    category_code: str = "HOUSING",
) -> tuple[int, int]:
    with SessionLocal() as db:
        category = db.scalar(select(Category).where(Category.code == category_code))
        assert category is not None

        policy = Policy(
            source="MANUAL",
            external_id=external_id,
            title="시뮬레이터 테스트 정책",
            summary="시뮬레이터 HTTP 테스트용 정책입니다.",
            application_end_date=date.today().replace(year=date.today().year + 1),
            status="ACTIVE",
            is_active=True,
        )
        db.add(policy)
        db.flush()
        db.add(
            PolicyCategory(
                policy_id=policy.id,
                category_id=category.id,
                is_primary=True,
            )
        )
        benefit = PolicyBenefit(
            policy_id=policy.id,
            benefit_type=benefit_type,
            amount_type=amount_type,
            calculation_rule_json=calculation_rule_json,
        )
        db.add(benefit)
        db.commit()
        db.refresh(benefit)
        return policy.id, benefit.id


def test_simulate_loan_interest_benefit_returns_exact_result(client: TestClient) -> None:
    headers = _authenticated_headers(client, email="simulate-loan@example.com")
    policy_id, benefit_id = _seed_policy_with_benefit(
        external_id="sim-http-loan",
        benefit_type="LOAN",
        amount_type="FORMULA",
        calculation_rule_json={
            "policy_interest_rate_percent": "1.8",
            "interest_reduction_rate_percent": "2.2",
            "max_loan_amount": "200000000",
            "max_support_months": 24,
            "repayment_type": "BULLET",
        },
        category_code="FINANCE",
    )

    response = client.post(
        f"/api/v1/policies/{policy_id}/benefits/{benefit_id}/simulate",
        json={"user_input": {"loan_amount": "100000000"}},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == TOP_LEVEL_RESULT_KEYS
    assert body["category"] == "LOAN_INTEREST"
    assert Decimal(str(body["total_benefit_amount"])) == Decimal("4400000.00")
    assert body["support_months"] == 24
    assert body["disclaimer"].strip()


def test_simulate_cash_benefit_with_housing_category_resolves_housing_rent(
    client: TestClient,
) -> None:
    headers = _authenticated_headers(client, email="simulate-housing@example.com")
    policy_id, benefit_id = _seed_policy_with_benefit(
        external_id="sim-http-housing",
        benefit_type="CASH",
        amount_type="FIXED",
        calculation_rule_json={"monthly_support_cap_amount": "200000", "support_months": 12},
        category_code="HOUSING",
    )

    response = client.post(
        f"/api/v1/policies/{policy_id}/benefits/{benefit_id}/simulate",
        json={"user_input": {"monthly_rent_amount": "300000"}},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["category"] == "HOUSING_RENT"
    assert Decimal(str(body["total_benefit_amount"])) == Decimal("2400000.00")


def test_simulate_requires_authentication(client: TestClient) -> None:
    policy_id, benefit_id = _seed_policy_with_benefit(
        external_id="sim-http-auth",
        benefit_type="LOAN",
        amount_type="FORMULA",
        calculation_rule_json={
            "policy_interest_rate_percent": "1.8",
            "interest_reduction_rate_percent": "2.2",
            "max_loan_amount": "200000000",
            "max_support_months": 24,
            "repayment_type": "BULLET",
        },
        category_code="FINANCE",
    )

    response = client.post(
        f"/api/v1/policies/{policy_id}/benefits/{benefit_id}/simulate",
        json={"user_input": {"loan_amount": "100000000"}},
    )

    assert response.status_code == 401


def test_simulate_returns_404_for_unknown_policy(client: TestClient) -> None:
    headers = _authenticated_headers(client, email="simulate-404-policy@example.com")

    response = client.post(
        "/api/v1/policies/999999/benefits/1/simulate",
        json={"user_input": {}},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_simulate_returns_404_for_unknown_benefit(client: TestClient) -> None:
    headers = _authenticated_headers(client, email="simulate-404-benefit@example.com")
    policy_id, _benefit_id = _seed_policy_with_benefit(
        external_id="sim-http-404-benefit",
        benefit_type="LOAN",
        amount_type="FORMULA",
        calculation_rule_json={
            "policy_interest_rate_percent": "1.8",
            "interest_reduction_rate_percent": "2.2",
            "max_loan_amount": "200000000",
            "max_support_months": 24,
            "repayment_type": "BULLET",
        },
        category_code="FINANCE",
    )

    response = client.post(
        f"/api/v1/policies/{policy_id}/benefits/999999/simulate",
        json={"user_input": {}},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_simulate_returns_422_for_service_benefit_with_no_calc_type(client: TestClient) -> None:
    headers = _authenticated_headers(client, email="simulate-422-unsupported@example.com")
    policy_id, benefit_id = _seed_policy_with_benefit(
        external_id="sim-http-service",
        benefit_type="SERVICE",
        amount_type="VARIABLE",
        calculation_rule_json=None,
        category_code="TRANSPORT",
    )

    response = client.post(
        f"/api/v1/policies/{policy_id}/benefits/{benefit_id}/simulate",
        json={"user_input": {}},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "SIMULATION_ERROR"


def test_simulate_returns_422_for_missing_required_user_input(client: TestClient) -> None:
    headers = _authenticated_headers(client, email="simulate-422-missing-input@example.com")
    policy_id, benefit_id = _seed_policy_with_benefit(
        external_id="sim-http-missing-input",
        benefit_type="LOAN",
        amount_type="FORMULA",
        calculation_rule_json={
            "policy_interest_rate_percent": "1.8",
            "interest_reduction_rate_percent": "2.2",
            "max_loan_amount": "200000000",
            "max_support_months": 24,
            "repayment_type": "BULLET",
        },
        category_code="FINANCE",
    )

    response = client.post(
        f"/api/v1/policies/{policy_id}/benefits/{benefit_id}/simulate",
        json={"user_input": {}},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "SIMULATION_ERROR"


def test_simulate_rejects_unknown_top_level_fields(client: TestClient) -> None:
    headers = _authenticated_headers(client, email="simulate-strict-payload@example.com")
    policy_id, benefit_id = _seed_policy_with_benefit(
        external_id="sim-http-strict",
        benefit_type="LOAN",
        amount_type="FORMULA",
        calculation_rule_json={
            "policy_interest_rate_percent": "1.8",
            "interest_reduction_rate_percent": "2.2",
            "max_loan_amount": "200000000",
            "max_support_months": 24,
            "repayment_type": "BULLET",
        },
        category_code="FINANCE",
    )

    response = client.post(
        f"/api/v1/policies/{policy_id}/benefits/{benefit_id}/simulate",
        json={"user_input": {"loan_amount": "100000000"}, "unexpected": "not allowed"},
        headers=headers,
    )

    assert response.status_code == 422
