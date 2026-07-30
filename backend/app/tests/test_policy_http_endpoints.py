"""HTTP coverage for policy discovery and the complete user-policy workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.policy import Policy, PolicyBenefit, PolicyCategory
from app.models.policy_condition import PolicyCondition
from app.models.policy_document import PolicyDocument
from app.models.user_category_profile import Category


@dataclass(frozen=True, slots=True)
class SeededPolicyIds:
    """Stable primary keys used across one isolated API test."""

    eligible_policy_id: int
    review_policy_id: int
    housing_category_id: int
    transport_category_id: int


def _authenticated_headers(client: TestClient, *, email: str) -> dict[str, str]:
    signup = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": "safe-password-123",
            "nickname": "정책테스터",
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
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.patch(
        "/api/v1/users/me/profile",
        headers=headers,
        json={
            "birth_year": date.today().year - 26,
            "region_code": "26",
            "region_sido": "부산광역시",
            "region_sigungu": "금정구",
            "income_band_code": "BETWEEN_75_100",
            "employment_status_code": "EMPLOYED",
            "household_type_code": "SINGLE",
            "household_size": 1,
            "housing_type_code": "MONTHLY_RENT",
            "onboarding_completed": True,
        },
    )
    assert profile.status_code == 200, profile.text
    assert profile.json()["onboarding_completed"] is True
    return headers


def _seed_policy_dataset() -> SeededPolicyIds:
    """Insert two policies with deterministic categories and match outcomes."""

    today = date.today()
    with SessionLocal() as db:
        housing = db.scalar(select(Category).where(Category.code == "HOUSING"))
        transport = db.scalar(select(Category).where(Category.code == "TRANSPORT"))
        assert housing is not None
        assert transport is not None

        eligible = Policy(
            source="MANUAL",
            external_id="http-test-eligible-housing",
            title="Alpha 청년 주거 지원",
            summary="추천 우선순위가 높은 주거 정책입니다.",
            description="만 19세부터 34세까지 신청할 수 있습니다.",
            support_target_text="만 19세부터 34세",
            support_content_text="월 20만 원, 최대 12개월",
            application_method="온라인 신청",
            provider_name="Alpha 기관",
            application_url="https://example.com/alpha",
            application_start_date=today - timedelta(days=10),
            application_end_date=today + timedelta(days=30),
            is_ongoing=False,
            published_date=date(2026, 1, 15),
            status="ACTIVE",
            subcategory="월세",
            region_scope="LOCAL",
            region_code="26",
            contact="051-000-0000",
            is_active=True,
        )
        review = Policy(
            source="MANUAL",
            external_id="http-test-review-transport",
            title="Beta 추가 확인 교통 지원",
            summary="서류 확인이 필요한 교통 정책입니다.",
            description="증빙 서류 검토 후 지원합니다.",
            support_target_text="임대차 계약 증빙 가능 청년",
            support_content_text="총 60만 원",
            application_method="방문 신청",
            provider_name="Beta 기관",
            application_url="https://example.com/beta",
            application_start_date=today - timedelta(days=5),
            application_end_date=today + timedelta(days=10),
            is_ongoing=False,
            published_date=date(2026, 2, 15),
            status="ACTIVE",
            subcategory="교통비",
            region_scope="NATIONAL",
            contact="02-000-0000",
            is_active=True,
        )
        db.add_all([eligible, review])
        db.flush()

        db.add_all(
            [
                PolicyCategory(
                    policy_id=eligible.id,
                    category_id=housing.id,
                    is_primary=True,
                ),
                PolicyCategory(
                    policy_id=review.id,
                    category_id=transport.id,
                    is_primary=True,
                ),
                PolicyCondition(
                    policy_id=eligible.id,
                    condition_key="profile.age",
                    operator="BETWEEN",
                    expected_value_json={"min": 19, "max": 34},
                    condition_group_no=1,
                    is_required=True,
                    check_mode="AUTO",
                    description="만 19세부터 34세",
                    failure_message="연령 기준을 충족하지 않습니다.",
                    sort_order=1,
                ),
                PolicyCondition(
                    policy_id=review.id,
                    condition_key="housing.rental_contract_verified",
                    operator="MANUAL_CHECK",
                    expected_value_json=None,
                    condition_group_no=1,
                    is_required=True,
                    check_mode="DOCUMENT",
                    description="임대차 계약 증빙 확인",
                    failure_message="임대차 계약 증빙이 필요합니다.",
                    sort_order=1,
                ),
                PolicyBenefit(
                    policy_id=eligible.id,
                    benefit_type="CASH",
                    amount_type="FIXED",
                    max_amount=Decimal("200000.00"),
                    payment_cycle="MONTHLY",
                    duration_months=12,
                    max_total_amount=Decimal("2400000.00"),
                    display_text="월 최대 20만 원",
                ),
                PolicyBenefit(
                    policy_id=review.id,
                    benefit_type="DISCOUNT",
                    amount_type="FIXED",
                    max_amount=Decimal("50000.00"),
                    payment_cycle="MONTHLY",
                    duration_months=12,
                    max_total_amount=Decimal("600000.00"),
                    display_text="총 최대 60만 원",
                ),
                PolicyDocument(
                    policy_id=eligible.id,
                    document_code="RESIDENT_REGISTRATION",
                    document_name="주민등록등본",
                    required_reason="거주지 확인",
                    issuing_organization="정부24",
                    issuing_method="온라인 발급",
                    issuing_url="https://www.gov.kr",
                    submission_format="PDF",
                    is_required=True,
                    display_order=1,
                ),
                PolicyDocument(
                    policy_id=review.id,
                    document_code="RENTAL_CONTRACT",
                    document_name="임대차계약서",
                    required_reason="계약 사실 확인",
                    issuing_organization="본인 보관",
                    issuing_method="스캔",
                    issuing_url=None,
                    submission_format="PDF",
                    is_required=True,
                    display_order=1,
                ),
            ]
        )
        db.commit()
        return SeededPolicyIds(
            eligible_policy_id=eligible.id,
            review_policy_id=review.id,
            housing_category_id=housing.id,
            transport_category_id=transport.id,
        )


def _as_decimal(value: object) -> Decimal:
    return Decimal(str(value))


def test_policy_discovery_match_and_bookmark_lifecycle(
    client: TestClient,
) -> None:
    """List, recommend, inspect, match, bookmark, and remove a policy."""

    headers = _authenticated_headers(client, email="policy-http@example.com")
    seeded = _seed_policy_dataset()

    policy_list = client.get(
        "/api/v1/policies",
        params={"sort": "recommendation", "page": 1, "size": 10},
        headers=headers,
    )
    assert policy_list.status_code == 200, policy_list.text
    list_body = policy_list.json()
    assert list_body["total"] == 2
    assert list_body["page"] == 1
    assert list_body["size"] == 10
    assert [item["id"] for item in list_body["items"]] == [
        seeded.eligible_policy_id,
        seeded.review_policy_id,
    ]
    assert [item["card_status"] for item in list_body["items"]] == [
        "ELIGIBLE",
        "NEEDS_REVIEW",
    ]
    assert _as_decimal(list_body["items"][0]["match_score"]) == Decimal("100.00")
    assert _as_decimal(list_body["items"][0]["estimated_benefit_amount"]) == Decimal("2400000.00")
    assert list_body["items"][0]["is_bookmarked"] is False

    housing_only = client.get(
        "/api/v1/policies",
        params={
            "category_code": "HOUSING",
            "eligibility_status": "ELIGIBLE",
            "sort": "latest",
            "page": 1,
            "size": 10,
        },
        headers=headers,
    )
    assert housing_only.status_code == 200, housing_only.text
    assert housing_only.json()["total"] == 1
    assert [item["id"] for item in housing_only.json()["items"]] == [seeded.eligible_policy_id]

    review_only = client.get(
        "/api/v1/policies",
        params={
            "category_code": "TRANSPORT",
            "eligibility_status": "NEEDS_REVIEW",
            "sort": "deadline",
        },
        headers=headers,
    )
    assert review_only.status_code == 200, review_only.text
    assert [item["id"] for item in review_only.json()["items"]] == [seeded.review_policy_id]

    latest = client.get(
        "/api/v1/policies",
        params={"sort": "latest"},
        headers=headers,
    )
    assert latest.status_code == 200, latest.text
    assert latest.json()["items"][0]["id"] == seeded.review_policy_id

    deadline = client.get(
        "/api/v1/policies",
        params={"sort": "deadline"},
        headers=headers,
    )
    assert deadline.status_code == 200, deadline.text
    assert deadline.json()["items"][0]["id"] == seeded.review_policy_id

    keyword = client.get(
        "/api/v1/policies",
        params={"keyword": "Alpha", "sort": "latest"},
        headers=headers,
    )
    assert keyword.status_code == 200, keyword.text
    assert keyword.json()["total"] == 1
    assert keyword.json()["items"][0]["id"] == seeded.eligible_policy_id

    recommendations = client.get(
        "/api/v1/users/me/recommendations",
        params={"limit": 1},
        headers=headers,
    )
    assert recommendations.status_code == 200, recommendations.text
    assert len(recommendations.json()) == 1
    assert recommendations.json()[0]["id"] == seeded.eligible_policy_id
    assert recommendations.json()[0]["card_status"] == "ELIGIBLE"

    detail = client.get(
        f"/api/v1/policies/{seeded.eligible_policy_id}",
        headers=headers,
    )
    assert detail.status_code == 200, detail.text
    detail_body = detail.json()
    assert detail_body["id"] == seeded.eligible_policy_id
    assert detail_body["title"] == "Alpha 청년 주거 지원"
    assert detail_body["description"] == "만 19세부터 34세까지 신청할 수 있습니다."
    assert detail_body["card_status"] == "ELIGIBLE"
    assert detail_body["categories"][0]["id"] == seeded.housing_category_id
    assert detail_body["categories"][0]["code"] == "HOUSING"
    assert detail_body["conditions"][0]["condition_key"] == "profile.age"
    assert detail_body["conditions"][0]["operator"] == "BETWEEN"
    assert detail_body["conditions"][0]["expected_value_json"] == {
        "min": 19,
        "max": 34,
    }
    assert _as_decimal(detail_body["benefits"][0]["max_total_amount"]) == Decimal("2400000.00")
    assert detail_body["documents"][0]["document_code"] == "RESIDENT_REGISTRATION"
    assert detail_body["is_bookmarked"] is False

    match = client.get(
        f"/api/v1/policies/{seeded.eligible_policy_id}/match",
        headers=headers,
    )
    assert match.status_code == 200, match.text
    match_body = match.json()
    assert match_body["policy_id"] == seeded.eligible_policy_id
    assert match_body["card_status"] == "ELIGIBLE"
    assert _as_decimal(match_body["match_score"]) == Decimal("100.00")
    assert match_body["satisfied_condition_count"] == 1
    assert match_body["review_condition_count"] == 0
    assert match_body["failed_condition_count"] == 0
    assert match_body["total_condition_count"] == 1
    assert match_body["conditions"][0]["condition_key"] == "profile.age"
    assert match_body["conditions"][0]["status"] == "충족"
    assert match_body["conditions"][0]["actual_value_json"] == {"value": 26}

    review_match = client.get(
        f"/api/v1/policies/{seeded.review_policy_id}/match",
        headers=headers,
    )
    assert review_match.status_code == 200, review_match.text
    assert review_match.json()["card_status"] == "NEEDS_REVIEW"
    assert review_match.json()["review_condition_count"] == 1
    assert review_match.json()["conditions"][0]["status"] == "추가 확인 필요"

    bookmark = client.post(
        f"/api/v1/policies/{seeded.eligible_policy_id}/bookmark",
        headers=headers,
    )
    assert bookmark.status_code == 201, bookmark.text
    assert bookmark.json()["policy_id"] == seeded.eligible_policy_id
    assert bookmark.json()["is_bookmarked"] is True
    assert bookmark.json()["bookmarked_at"] is not None

    bookmarked_detail = client.get(
        f"/api/v1/policies/{seeded.eligible_policy_id}",
        headers=headers,
    )
    assert bookmarked_detail.status_code == 200, bookmarked_detail.text
    assert bookmarked_detail.json()["is_bookmarked"] is True

    bookmarked_list = client.get(
        "/api/v1/users/me/policies",
        params={"tab": "bookmarked"},
        headers=headers,
    )
    assert bookmarked_list.status_code == 200, bookmarked_list.text
    assert [item["policy_id"] for item in bookmarked_list.json()] == [seeded.eligible_policy_id]

    removed = client.delete(
        f"/api/v1/policies/{seeded.eligible_policy_id}/bookmark",
        headers=headers,
    )
    assert removed.status_code == 204
    assert removed.content == b""

    after_delete = client.get(
        f"/api/v1/policies/{seeded.eligible_policy_id}",
        headers=headers,
    )
    assert after_delete.status_code == 200, after_delete.text
    assert after_delete.json()["is_bookmarked"] is False

    no_bookmarks = client.get(
        "/api/v1/users/me/policies",
        params={"tab": "bookmarked"},
        headers=headers,
    )
    assert no_bookmarks.status_code == 200, no_bookmarks.text
    assert no_bookmarks.json() == []

    all_states = client.get("/api/v1/users/me/policies", headers=headers)
    assert all_states.status_code == 200, all_states.text
    deleted_bookmark_state = next(
        item for item in all_states.json() if item["policy_id"] == seeded.eligible_policy_id
    )
    assert deleted_bookmark_state["is_bookmarked"] is False
    assert deleted_bookmark_state["preparation_status"] == "NOT_STARTED"


def test_checklist_application_and_missing_resource_responses(
    client: TestClient,
) -> None:
    """Drive review confirmation, document progress, and application state."""

    headers = _authenticated_headers(client, email="checklist-http@example.com")
    seeded = _seed_policy_dataset()

    started = client.post(
        f"/api/v1/policies/{seeded.review_policy_id}/preparation",
        headers=headers,
    )
    assert started.status_code == 201, started.text
    started_body = started.json()
    assert started_body["policy_id"] == seeded.review_policy_id
    assert started_body["policy_title"] == "Beta 추가 확인 교통 지원"
    assert started_body["preparation_status"] == "IN_PROGRESS"
    assert started_body["progress_percent"] == 0
    assert len(started_body["conditions"]) == 1
    assert len(started_body["documents"]) == 1
    assert started_body["conditions"][0]["result_status"] == "NEEDS_REVIEW"
    assert started_body["conditions"][0]["is_user_confirmed"] is False
    assert started_body["documents"][0]["preparation_status"] == "NOT_STARTED"
    assert started_body["documents"][0]["is_checked"] is False

    state_id = started_body["state_id"]
    condition_id = started_body["conditions"][0]["condition_id"]
    document_id = started_body["documents"][0]["document_id"]

    resumed = client.get(
        f"/api/v1/preparations/{state_id}",
        headers=headers,
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["state_id"] == state_id
    assert resumed.json()["progress_percent"] == 0

    confirmed = client.patch(
        f"/api/v1/preparations/{state_id}/conditions/{condition_id}",
        headers=headers,
        json={"confirmed": True},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["progress_percent"] == 50
    assert confirmed.json()["preparation_status"] == "IN_PROGRESS"
    assert confirmed.json()["conditions"][0]["is_user_confirmed"] is True
    assert confirmed.json()["conditions"][0]["confirmed_at"] is not None

    document_ready = client.patch(
        f"/api/v1/preparations/{state_id}/documents/{document_id}",
        headers=headers,
        json={
            "preparation_status": "READY",
            "is_checked": True,
            "note": "스캔 및 검토 완료",
        },
    )
    assert document_ready.status_code == 200, document_ready.text
    ready_body = document_ready.json()
    assert ready_body["progress_percent"] == 100
    assert ready_body["preparation_status"] == "COMPLETED"
    assert ready_body["documents"][0]["document_id"] == document_id
    assert ready_body["documents"][0]["preparation_status"] == "READY"
    assert ready_body["documents"][0]["is_checked"] is True
    assert ready_body["documents"][0]["checked_at"] is not None
    assert ready_body["documents"][0]["note"] == "스캔 및 검토 완료"

    completed = client.get(
        f"/api/v1/preparations/{state_id}",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["progress_percent"] == 100
    assert completed.json()["preparation_status"] == "COMPLETED"

    application_date = date(2026, 7, 29)
    application = client.post(
        f"/api/v1/policies/{seeded.review_policy_id}/applications",
        headers=headers,
        json={
            "application_date": application_date.isoformat(),
            "application_status": "SUBMITTED",
            "application_note": "온라인 접수 완료",
        },
    )
    assert application.status_code == 200, application.text
    application_body = application.json()
    assert application_body["state_id"] == state_id
    assert application_body["policy_id"] == seeded.review_policy_id
    assert application_body["application_status"] == "SUBMITTED"
    assert application_body["application_date"] == application_date.isoformat()
    assert application_body["preparation_status"] == "COMPLETED"
    assert application_body["progress_percent"] == 100
    assert application_body["eligibility_status"] == "NEEDS_REVIEW"
    assert _as_decimal(application_body["match_score"]) == Decimal("0.00")

    applied = client.get(
        "/api/v1/users/me/policies",
        params={"tab": "applied", "sort": "deadline"},
        headers=headers,
    )
    assert applied.status_code == 200, applied.text
    assert len(applied.json()) == 1
    assert applied.json()[0]["policy_id"] == seeded.review_policy_id
    assert applied.json()[0]["application_status"] == "SUBMITTED"

    no_longer_preparing = client.get(
        "/api/v1/users/me/policies",
        params={"tab": "preparing"},
        headers=headers,
    )
    assert no_longer_preparing.status_code == 200, no_longer_preparing.text
    assert no_longer_preparing.json() == []

    missing_state = state_id + 100_000
    missing_preparation = client.get(
        f"/api/v1/preparations/{missing_state}",
        headers=headers,
    )
    assert missing_preparation.status_code == 404
    assert missing_preparation.json()["code"] == "NOT_FOUND"

    missing_document = client.patch(
        f"/api/v1/preparations/{state_id}/documents/{document_id + 100_000}",
        headers=headers,
        json={
            "preparation_status": "READY",
            "is_checked": True,
            "note": None,
        },
    )
    assert missing_document.status_code == 404
    assert missing_document.json()["code"] == "NOT_FOUND"

    missing_condition = client.patch(
        f"/api/v1/preparations/{state_id}/conditions/{condition_id + 100_000}",
        headers=headers,
        json={"confirmed": True},
    )
    assert missing_condition.status_code == 404
    assert missing_condition.json()["code"] == "NOT_FOUND"

    missing_policy_id = (
        max(
            seeded.eligible_policy_id,
            seeded.review_policy_id,
        )
        + 100_000
    )
    missing_requests = (
        client.get(
            f"/api/v1/policies/{missing_policy_id}",
            headers=headers,
        ),
        client.get(
            f"/api/v1/policies/{missing_policy_id}/match",
            headers=headers,
        ),
        client.post(
            f"/api/v1/policies/{missing_policy_id}/bookmark",
            headers=headers,
        ),
        client.delete(
            f"/api/v1/policies/{missing_policy_id}/bookmark",
            headers=headers,
        ),
        client.post(
            f"/api/v1/policies/{missing_policy_id}/preparation",
            headers=headers,
        ),
        client.post(
            f"/api/v1/policies/{missing_policy_id}/applications",
            headers=headers,
            json={
                "application_date": application_date.isoformat(),
                "application_status": "SUBMITTED",
                "application_note": None,
            },
        ),
    )
    for response in missing_requests:
        assert response.status_code == 404, response.text
        assert response.json()["code"] == "NOT_FOUND"
