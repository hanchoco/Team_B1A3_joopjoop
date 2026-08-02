"""End-to-end API flow for signup, matching, bookmark, and checklist."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.crud.categories import get_category_by_code
from app.db.session import SessionLocal
from app.models.policy import Policy, PolicyBenefit, PolicyCategory
from app.models.policy_condition import PolicyCondition
from app.models.policy_document import PolicyDocument


def _signup(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "youth@example.com",
            "password": "safe-password-123",
            "nickname": "줍줍이",
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
    assert response.status_code == 201, response.text
    return str(response.json()["access_token"])


def _seed_policy() -> tuple[int, int]:
    with SessionLocal() as db:
        category = get_category_by_code(db, "HOUSING")
        assert category is not None
        policy = Policy(
            source="MANUAL",
            external_id="housing-test-1",
            title="청년 주거비 지원",
            summary="월세를 매월 지원합니다.",
            description="만 19세부터 34세까지 신청할 수 있습니다.",
            support_target_text="만 19세부터 34세",
            support_content_text="월 20만 원, 최대 12개월",
            provider_name="테스트 기관",
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
        db.add(
            PolicyCondition(
                policy_id=policy.id,
                condition_key="profile.age",
                operator="BETWEEN",
                expected_value_json={"min": 19, "max": 34},
                condition_group_no=1,
                check_mode="AUTO",
                description="만 19세부터 34세",
                sort_order=1,
            )
        )
        benefit = PolicyBenefit(
            policy_id=policy.id,
            benefit_type="CASH",
            amount_type="FIXED",
            max_amount=Decimal("200000"),
            payment_cycle="MONTHLY",
            duration_months=12,
            max_total_amount=Decimal("2400000"),
            display_text="월 최대 20만 원",
            calculation_rule_json={
                "monthly_support_cap_amount": "200000",
                "support_months": 12,
            },
        )
        db.add(benefit)
        db.add(
            PolicyDocument(
                policy_id=policy.id,
                document_code="RESIDENT_REGISTRATION",
                document_name="주민등록등본",
                required_reason="거주지 확인",
                issuing_organization="정부24",
                issuing_url="https://www.gov.kr",
                is_required=True,
                display_order=1,
            )
        )
        db.commit()
        return policy.id, benefit.id


def test_policy_recommendation_and_checklist_flow(client: TestClient) -> None:
    """All-satisfied cards stay two-state while detail conditions stay three-state."""

    token = _signup(client)
    headers = {"Authorization": f"Bearer {token}"}
    profile_response = client.patch(
        "/api/v1/users/me/profile",
        headers=headers,
        json={
            "birth_year": date.today().year - 26,
            "region_code": "26",
            "region_sido": "부산광역시",
            "income_band_code": "BETWEEN_75_100",
            "employment_status_code": "EMPLOYED",
            "household_type_code": "SINGLE",
            "household_size": 1,
            "housing_type_code": "MONTHLY_RENT",
            "onboarding_completed": True,
        },
    )
    assert profile_response.status_code == 200, profile_response.text

    policy_id, _benefit_id = _seed_policy()
    list_response = client.get(
        "/api/v1/policies?sort=recommendation",
        headers=headers,
    )
    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["items"][0]["card_status"] == "ELIGIBLE"

    match_response = client.get(
        f"/api/v1/policies/{policy_id}/match",
        headers=headers,
    )
    assert match_response.status_code == 200, match_response.text
    assert match_response.json()["conditions"][0]["status"] == "충족"

    bookmark_response = client.post(
        f"/api/v1/policies/{policy_id}/bookmark",
        headers=headers,
    )
    assert bookmark_response.status_code == 201, bookmark_response.text

    preparation_response = client.post(
        f"/api/v1/policies/{policy_id}/preparation",
        headers=headers,
    )
    assert preparation_response.status_code == 201, preparation_response.text
    preparation = preparation_response.json()
    assert preparation["progress_percent"] == 50

    state_id = preparation["state_id"]
    document_id = preparation["documents"][0]["document_id"]
    completed_response = client.patch(
        f"/api/v1/preparations/{state_id}/documents/{document_id}",
        headers=headers,
        json={
            "preparation_status": "READY",
            "is_checked": True,
            "note": "발급 완료",
        },
    )
    assert completed_response.status_code == 200, completed_response.text
    assert completed_response.json()["progress_percent"] == 100


def test_simulator_inputs_are_transient(client: TestClient) -> None:
    """Simulator accepts per-request user_input without persisting it anywhere."""

    token = _signup(client)
    headers = {"Authorization": f"Bearer {token}"}
    policy_id, benefit_id = _seed_policy()

    response = client.post(
        f"/api/v1/policies/{policy_id}/benefits/{benefit_id}/simulate",
        headers=headers,
        json={"user_input": {"monthly_rent_amount": "500000"}},
    )
    assert response.status_code == 200, response.text
    assert response.json()["category"] == "HOUSING_RENT"
    assert response.json()["monthly_before_amount"] == "500000.00"
    assert response.json()["monthly_after_amount"] == "300000.00"
