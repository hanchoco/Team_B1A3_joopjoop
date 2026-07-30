"""Scenario tests for authentication, user settings, and category answers."""

from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import AccountStatus, User
from app.models.user_category_profile import (
    AnswerType,
    Category,
    CategoryCode,
    CategoryQuestion,
    UserCategoryAnswer,
)

USER_RESPONSE_KEYS = {
    "id",
    "email",
    "nickname",
    "account_status",
    "last_login_at",
    "created_at",
    "updated_at",
}
PROFILE_RESPONSE_KEYS = {
    "user_id",
    "birth_year",
    "region_code",
    "region_sido",
    "region_sigungu",
    "income_band_code",
    "employment_status_code",
    "household_type_code",
    "household_size",
    "housing_type_code",
    "onboarding_completed",
    "created_at",
    "updated_at",
}
CONSENT_RESPONSE_KEYS = {
    "id",
    "user_id",
    "consent_type",
    "consent_version",
    "is_agreed",
    "agreed_at",
    "withdrawn_at",
    "created_at",
    "updated_at",
}


def _assert_iso_datetime(value: object) -> None:
    """Require a non-empty ISO-8601 datetime string."""

    assert isinstance(value, str)
    assert value
    datetime.fromisoformat(value.replace("Z", "+00:00"))


def _assert_user_response(
    payload: dict[str, object],
    *,
    user_id: int,
    email: str,
    nickname: str,
    last_login_expected: bool,
) -> None:
    """Assert the complete public user response contract."""

    assert set(payload) == USER_RESPONSE_KEYS
    assert payload["id"] == user_id
    assert payload["email"] == email
    assert payload["nickname"] == nickname
    assert payload["account_status"] == "ACTIVE"
    if last_login_expected:
        _assert_iso_datetime(payload["last_login_at"])
    else:
        assert payload["last_login_at"] is None
    _assert_iso_datetime(payload["created_at"])
    _assert_iso_datetime(payload["updated_at"])


def _signup(
    client: TestClient,
    *,
    email: str,
    password: str,
    nickname: str,
) -> tuple[str, int]:
    """Create a user with both required consents and return its token/id."""

    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": password,
            "nickname": nickname,
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
    body = response.json()
    assert set(body) == {"access_token", "token_type", "user"}
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]
    assert isinstance(body["user"], dict)
    user_id = body["user"]["id"]
    assert isinstance(user_id, int)
    assert user_id > 0
    _assert_user_response(
        body["user"],
        user_id=user_id,
        email=email.lower(),
        nickname=nickname,
        last_login_expected=False,
    )
    return body["access_token"], user_id


def test_auth_user_profile_account_consent_and_withdrawal_flow(
    client: TestClient,
) -> None:
    """Exercise a user's complete account lifecycle with exact readbacks."""

    original_email = "lifecycle@example.com"
    original_password = "safe-password-123"
    original_nickname = "첫닉네임"
    signup_response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": original_email.upper(),
            "password": original_password,
            "nickname": original_nickname,
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
                {
                    "consent_type": "MARKETING_OPTIONAL",
                    "consent_version": "1.0",
                    "is_agreed": False,
                },
            ],
        },
    )
    assert signup_response.status_code == 201, signup_response.text
    signup = signup_response.json()
    assert set(signup) == {"access_token", "token_type", "user"}
    assert signup["token_type"] == "bearer"
    assert isinstance(signup["access_token"], str)
    assert signup["access_token"]
    signup_user = signup["user"]
    assert isinstance(signup_user, dict)
    user_id = signup_user["id"]
    assert isinstance(user_id, int)
    assert user_id > 0
    _assert_user_response(
        signup_user,
        user_id=user_id,
        email=original_email,
        nickname=original_nickname,
        last_login_expected=False,
    )

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": original_email, "password": original_password},
    )
    assert login_response.status_code == 200, login_response.text
    login = login_response.json()
    assert set(login) == {"access_token", "token_type", "user"}
    assert login["token_type"] == "bearer"
    assert isinstance(login["access_token"], str)
    assert login["access_token"]
    login_user = login["user"]
    assert isinstance(login_user, dict)
    _assert_user_response(
        login_user,
        user_id=user_id,
        email=original_email,
        nickname=original_nickname,
        last_login_expected=True,
    )
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    account_response = client.get("/api/v1/users/me", headers=headers)
    assert account_response.status_code == 200, account_response.text
    assert account_response.json() == login_user

    initial_profile_response = client.get(
        "/api/v1/users/me/profile",
        headers=headers,
    )
    assert initial_profile_response.status_code == 200, initial_profile_response.text
    initial_profile = initial_profile_response.json()
    assert set(initial_profile) == PROFILE_RESPONSE_KEYS
    assert initial_profile == {
        "user_id": user_id,
        "birth_year": None,
        "region_code": None,
        "region_sido": None,
        "region_sigungu": None,
        "income_band_code": None,
        "employment_status_code": None,
        "household_type_code": None,
        "household_size": None,
        "housing_type_code": None,
        "onboarding_completed": False,
        "created_at": initial_profile["created_at"],
        "updated_at": initial_profile["updated_at"],
    }
    _assert_iso_datetime(initial_profile["created_at"])
    _assert_iso_datetime(initial_profile["updated_at"])

    profile_update = {
        "birth_year": 1998,
        "region_code": "26",
        "region_sido": "부산광역시",
        "region_sigungu": "금정구",
        "income_band_code": "BETWEEN_75_100",
        "employment_status_code": "EMPLOYED",
        "household_type_code": "SINGLE",
        "household_size": 1,
        "housing_type_code": "MONTHLY_RENT",
        "onboarding_completed": True,
    }
    profile_update_response = client.patch(
        "/api/v1/users/me/profile",
        headers=headers,
        json=profile_update,
    )
    assert profile_update_response.status_code == 200, profile_update_response.text
    updated_profile = profile_update_response.json()
    assert set(updated_profile) == PROFILE_RESPONSE_KEYS
    assert updated_profile["user_id"] == user_id
    for field, expected in profile_update.items():
        assert updated_profile[field] == expected
    assert updated_profile["created_at"] == initial_profile["created_at"]
    _assert_iso_datetime(updated_profile["updated_at"])

    profile_readback_response = client.get(
        "/api/v1/users/me/profile",
        headers=headers,
    )
    assert profile_readback_response.status_code == 200, profile_readback_response.text
    assert profile_readback_response.json() == updated_profile

    password_verification_response = client.post(
        "/api/v1/users/me/verify-password",
        headers=headers,
        json={"current_password": original_password},
    )
    assert password_verification_response.status_code == 200
    password_verification = password_verification_response.json()
    assert set(password_verification) == {"message"}
    assert isinstance(password_verification["message"], str)
    assert password_verification["message"]

    new_email = "changed@example.com"
    new_password = "new-safe-password-456"
    new_nickname = "변경닉네임"
    account_update_response = client.patch(
        "/api/v1/users/me/account",
        headers=headers,
        json={
            "current_password": original_password,
            "email": new_email.upper(),
            "new_password": new_password,
            "new_password_confirm": new_password,
            "nickname": new_nickname,
        },
    )
    assert account_update_response.status_code == 200, account_update_response.text
    updated_account = account_update_response.json()
    _assert_user_response(
        updated_account,
        user_id=user_id,
        email=new_email,
        nickname=new_nickname,
        last_login_expected=True,
    )

    account_readback_response = client.get("/api/v1/users/me", headers=headers)
    assert account_readback_response.status_code == 200, account_readback_response.text
    assert account_readback_response.json() == updated_account

    old_login_response = client.post(
        "/api/v1/auth/login",
        json={"email": original_email, "password": original_password},
    )
    assert old_login_response.status_code == 401
    assert set(old_login_response.json()) == {"code", "detail"}
    assert old_login_response.json()["code"] == "AUTHENTICATION_FAILED"

    new_login_response = client.post(
        "/api/v1/auth/login",
        json={"email": new_email, "password": new_password},
    )
    assert new_login_response.status_code == 200, new_login_response.text
    new_login = new_login_response.json()
    assert set(new_login) == {"access_token", "token_type", "user"}
    assert new_login["token_type"] == "bearer"
    assert isinstance(new_login["access_token"], str)
    assert new_login["access_token"]
    assert isinstance(new_login["user"], dict)
    _assert_user_response(
        new_login["user"],
        user_id=user_id,
        email=new_email,
        nickname=new_nickname,
        last_login_expected=True,
    )
    current_headers = {"Authorization": f"Bearer {new_login['access_token']}"}

    initial_consents_response = client.get(
        "/api/v1/users/me/consents",
        headers=current_headers,
    )
    assert initial_consents_response.status_code == 200, initial_consents_response.text
    initial_consents = initial_consents_response.json()
    assert len(initial_consents) == 3
    initial_by_key = {
        (consent["consent_type"], consent["consent_version"]): consent
        for consent in initial_consents
    }
    assert set(initial_by_key) == {
        ("TERMS_REQUIRED", "1.0"),
        ("PRIVACY_REQUIRED", "1.0"),
        ("MARKETING_OPTIONAL", "1.0"),
    }
    for consent in initial_consents:
        assert set(consent) == CONSENT_RESPONSE_KEYS
        assert consent["user_id"] == user_id
        _assert_iso_datetime(consent["agreed_at"])
        _assert_iso_datetime(consent["created_at"])
        _assert_iso_datetime(consent["updated_at"])
    assert initial_by_key[("TERMS_REQUIRED", "1.0")]["is_agreed"] is True
    assert initial_by_key[("TERMS_REQUIRED", "1.0")]["withdrawn_at"] is None
    assert initial_by_key[("PRIVACY_REQUIRED", "1.0")]["is_agreed"] is True
    assert initial_by_key[("PRIVACY_REQUIRED", "1.0")]["withdrawn_at"] is None
    assert initial_by_key[("MARKETING_OPTIONAL", "1.0")]["is_agreed"] is False
    _assert_iso_datetime(initial_by_key[("MARKETING_OPTIONAL", "1.0")]["withdrawn_at"])

    consent_update_response = client.put(
        "/api/v1/users/me/consents",
        headers=current_headers,
        json={
            "consents": [
                {
                    "consent_type": "MARKETING_OPTIONAL",
                    "consent_version": "1.0",
                    "is_agreed": True,
                },
                {
                    "consent_type": "TERMS_REQUIRED",
                    "consent_version": "2.0",
                    "is_agreed": True,
                },
            ]
        },
    )
    assert consent_update_response.status_code == 200, consent_update_response.text
    updated_consents = consent_update_response.json()
    assert len(updated_consents) == 2
    assert [
        (item["consent_type"], item["consent_version"], item["is_agreed"])
        for item in updated_consents
    ] == [
        ("MARKETING_OPTIONAL", "1.0", True),
        ("TERMS_REQUIRED", "2.0", True),
    ]
    for consent in updated_consents:
        assert set(consent) == CONSENT_RESPONSE_KEYS
        assert consent["user_id"] == user_id
        assert consent["withdrawn_at"] is None

    consent_readback_response = client.get(
        "/api/v1/users/me/consents",
        headers=current_headers,
    )
    assert consent_readback_response.status_code == 200, consent_readback_response.text
    consent_readback = consent_readback_response.json()
    assert len(consent_readback) == 4
    readback_by_id = {consent["id"]: consent for consent in consent_readback}
    for updated_consent in updated_consents:
        assert readback_by_id[updated_consent["id"]] == updated_consent

    withdrawal_response = client.request(
        "DELETE",
        "/api/v1/users/me",
        headers=current_headers,
        json={
            "current_password": new_password,
            "confirm_withdrawal": True,
        },
    )
    assert withdrawal_response.status_code == 200, withdrawal_response.text
    withdrawal = withdrawal_response.json()
    assert set(withdrawal) == {"message"}
    assert isinstance(withdrawal["message"], str)
    assert withdrawal["message"]

    with SessionLocal() as db:
        withdrawn_user = db.get(User, user_id)
        assert withdrawn_user is not None
        assert withdrawn_user.email == new_email
        assert withdrawn_user.account_status == AccountStatus.WITHDRAWN
        assert withdrawn_user.deleted_at is not None

    denied_response = client.get("/api/v1/users/me", headers=current_headers)
    assert denied_response.status_code == 401
    denied = denied_response.json()
    assert set(denied) == {"code", "detail"}
    assert denied["code"] == "AUTHENTICATION_FAILED"
    assert isinstance(denied["detail"], str)
    assert denied["detail"]

    withdrawn_login_response = client.post(
        "/api/v1/auth/login",
        json={"email": new_email, "password": new_password},
    )
    assert withdrawn_login_response.status_code == 401
    assert set(withdrawn_login_response.json()) == {"code", "detail"}
    assert withdrawn_login_response.json()["code"] == "AUTHENTICATION_FAILED"


def test_categories_questions_and_answer_upsert(client: TestClient) -> None:
    """Read public category metadata and persist one reusable answer."""

    options = [
        {"label": "가입", "value": "ENROLLED"},
        {"label": "미가입", "value": "NOT_ENROLLED"},
    ]
    with SessionLocal() as db:
        category = db.scalar(select(Category).where(Category.code == CategoryCode.EMPLOYMENT))
        assert category is not None
        question = CategoryQuestion(
            category_id=category.id,
            question_key="employment.test_probe_question",
            label="고용보험 가입 여부",
            description="현재 고용보험 가입 상태를 선택하세요.",
            answer_type=AnswerType.SINGLE_SELECT,
            options_json=options,
            unit=None,
            is_required=True,
            is_used_for_matching=True,
            display_order=99,
            is_active=True,
        )
        db.add(question)
        db.commit()
        db.refresh(question)
        category_id = category.id
        question_id = question.id

    categories_response = client.get("/api/v1/categories")
    assert categories_response.status_code == 200, categories_response.text
    categories = categories_response.json()
    assert len(categories) == 8
    assert [item["code"] for item in categories] == [
        "HOUSING",
        "TRANSPORT",
        "FINANCE",
        "TAX",
        "EMPLOYMENT",
        "WELFARE",
        "PARTICIPATION",
        "ETC",
    ]
    assert [item["display_order"] for item in categories] == list(range(1, 9))
    for item in categories:
        assert set(item) == {
            "id",
            "code",
            "name",
            "description",
            "display_order",
            "is_active",
            "questions",
        }
        assert isinstance(item["id"], int)
        assert item["id"] > 0
        assert item["is_active"] is True
        assert item["questions"] == []
    employment_category = next(item for item in categories if item["code"] == "EMPLOYMENT")
    assert employment_category["id"] == category_id

    questions_response = client.get(f"/api/v1/categories/{category_id}/questions")
    assert questions_response.status_code == 200, questions_response.text
    questions_payload = questions_response.json()
    # 5 seeded EMPLOYMENT default questions + the manually created probe question above.
    assert len(questions_payload) == 6
    manual_question = next(item for item in questions_payload if item["id"] == question_id)
    assert manual_question == {
        "id": question_id,
        "category_id": category_id,
        "question_key": "employment.test_probe_question",
        "label": "고용보험 가입 여부",
        "description": "현재 고용보험 가입 상태를 선택하세요.",
        "answer_type": "SINGLE_SELECT",
        "options_json": options,
        "unit": None,
        "is_required": True,
        "is_used_for_matching": True,
        "display_order": 99,
        "is_active": True,
    }

    missing_category_response = client.get("/api/v1/categories/999999/questions")
    assert missing_category_response.status_code == 404
    missing_category = missing_category_response.json()
    assert set(missing_category) == {"code", "detail"}
    assert missing_category["code"] == "NOT_FOUND"
    assert isinstance(missing_category["detail"], str)
    assert missing_category["detail"]

    unauthenticated_answer_response = client.put(
        f"/api/v1/categories/{category_id}/answers",
        json={
            "answers": [
                {
                    "question_id": question_id,
                    "answer_json": {"value": "ENROLLED"},
                }
            ]
        },
    )
    assert unauthenticated_answer_response.status_code == 401
    assert set(unauthenticated_answer_response.json()) == {"code", "detail"}
    assert unauthenticated_answer_response.json()["code"] == "AUTHENTICATION_FAILED"

    token, user_id = _signup(
        client,
        email="category-answer@example.com",
        password="category-password-123",
        nickname="카테고리사용자",
    )
    headers = {"Authorization": f"Bearer {token}"}

    create_answer_response = client.put(
        f"/api/v1/categories/{category_id}/answers",
        headers=headers,
        json={
            "answers": [
                {
                    "question_id": question_id,
                    "answer_json": {"value": "ENROLLED"},
                }
            ]
        },
    )
    assert create_answer_response.status_code == 200, create_answer_response.text
    created_answers = create_answer_response.json()
    assert len(created_answers) == 1
    created_answer = created_answers[0]
    assert set(created_answer) == {
        "id",
        "user_id",
        "question_id",
        "answer_json",
        "answered_at",
        "updated_at",
    }
    assert isinstance(created_answer["id"], int)
    assert created_answer["id"] > 0
    assert created_answer["user_id"] == user_id
    assert created_answer["question_id"] == question_id
    assert created_answer["answer_json"] == {"value": "ENROLLED"}
    _assert_iso_datetime(created_answer["answered_at"])
    _assert_iso_datetime(created_answer["updated_at"])

    update_answer_response = client.put(
        f"/api/v1/categories/{category_id}/answers",
        headers=headers,
        json={
            "answers": [
                {
                    "question_id": question_id,
                    "answer_json": {"value": "NOT_ENROLLED"},
                }
            ]
        },
    )
    assert update_answer_response.status_code == 200, update_answer_response.text
    assert len(update_answer_response.json()) == 1
    updated_answer = update_answer_response.json()[0]
    assert set(updated_answer) == set(created_answer)
    assert updated_answer["id"] == created_answer["id"]
    assert updated_answer["user_id"] == user_id
    assert updated_answer["question_id"] == question_id
    assert updated_answer["answer_json"] == {"value": "NOT_ENROLLED"}
    assert updated_answer["answered_at"] == created_answer["answered_at"]
    _assert_iso_datetime(updated_answer["updated_at"])

    with SessionLocal() as db:
        stored_answers = list(
            db.scalars(
                select(UserCategoryAnswer).where(
                    UserCategoryAnswer.user_id == user_id,
                    UserCategoryAnswer.question_id == question_id,
                )
            ).all()
        )
        assert len(stored_answers) == 1
        assert stored_answers[0].id == created_answer["id"]
        assert stored_answers[0].answer_json == {"value": "NOT_ENROLLED"}


def test_default_category_questions_are_seeded(client: TestClient) -> None:
    """ensure_default_category_questions() seeds one onboarding question set per category."""

    categories_response = client.get("/api/v1/categories")
    assert categories_response.status_code == 200, categories_response.text
    categories_by_code = {item["code"]: item["id"] for item in categories_response.json()}

    expected_counts = {
        "EMPLOYMENT": 5,
        "HOUSING": 5,
        "FINANCE": 5,
        "WELFARE": 2,
    }
    for code, expected_count in expected_counts.items():
        category_id = categories_by_code[code]
        questions_response = client.get(f"/api/v1/categories/{category_id}/questions")
        assert questions_response.status_code == 200, questions_response.text
        questions = questions_response.json()
        assert len(questions) == expected_count, code
        assert all(question["is_required"] is False for question in questions)
        assert all(question["is_used_for_matching"] is True for question in questions)
        assert all(question["is_active"] is True for question in questions)
