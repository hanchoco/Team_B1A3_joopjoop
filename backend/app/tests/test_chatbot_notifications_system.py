#!/usr/bin/env python3
"""Integration coverage for chatbot, notifications, and system health."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import main
from app.db.session import SessionLocal
from app.models.policy import Policy
from app.models.policy_condition import PolicyCondition
from app.models.user_policy import UserPolicyState
from app.services.ai.solar_client import SolarClient, SolarClientError
from app.services.notification.scheduler import KST
from app.services.notification_service import create_due_deadline_notifications

_PASSWORD = "safe-password-123"
_SUGGESTED_QUESTIONS = [
    "제가 이 정책에 지원할 수 있나요?",
    "필요한 서류는 무엇인가요?",
    "소득 기준은 어떻게 계산하나요?",
    "신청 절차가 궁금합니다.",
]
_SETTING_KEYS = {
    "user_id",
    "notification_enabled",
    "deadline_d7_enabled",
    "deadline_d3_enabled",
    "deadline_d0_enabled",
    "email_enabled",
    "push_enabled",
    "updated_at",
}
_NOTIFICATION_KEYS = {
    "id",
    "policy_id",
    "notification_type",
    "title",
    "body",
    "scheduled_at",
    "sent_at",
    "read_at",
    "send_status",
}


def _signup(
    client: TestClient,
    *,
    email: str = "notification-user@example.com",
) -> tuple[str, int]:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": _PASSWORD,
            "nickname": "알림 테스트 사용자",
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
    assert body["user"]["email"] == email
    return str(body["access_token"]), int(body["user"]["id"])


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_policy(
    *,
    external_id: str,
    title: str,
    application_end_date: date,
    is_ongoing: bool = False,
    is_active: bool = True,
    with_condition: bool = False,
) -> int:
    with SessionLocal() as db:
        policy = Policy(
            source="MANUAL",
            external_id=external_id,
            title=title,
            summary=f"{title} 요약",
            description=f"{title} 상세 설명",
            support_target_text="만 19세부터 34세",
            support_content_text="월 최대 20만 원",
            application_method="온라인 신청",
            provider_name="테스트 기관",
            application_url="https://example.com/apply",
            application_start_date=date(2026, 1, 1),
            application_end_date=application_end_date,
            is_ongoing=is_ongoing,
            status="ACTIVE",
            contact="051-000-0000",
            original_text=f"{title}의 원문",
            is_active=is_active,
        )
        db.add(policy)
        db.flush()
        if with_condition:
            db.add(
                PolicyCondition(
                    policy_id=policy.id,
                    condition_key="profile.age",
                    operator="BETWEEN",
                    expected_value_json={"min": 19, "max": 34},
                    condition_group_no=1,
                    is_required=True,
                    check_mode="AUTO",
                    description="만 19세부터 34세",
                    failure_message="연령 조건을 확인하세요.",
                    sort_order=0,
                )
            )
        db.commit()
        return policy.id


def _bookmark_policy(*, user_id: int, policy_id: int, bookmarked: bool) -> None:
    with SessionLocal() as db:
        db.add(
            UserPolicyState(
                user_id=user_id,
                policy_id=policy_id,
                is_bookmarked=bookmarked,
                bookmarked_at=(
                    datetime(2026, 7, 1, 9, 0, tzinfo=UTC).replace(tzinfo=None)
                    if bookmarked
                    else None
                ),
                preparation_status="NOT_STARTED",
                progress_percent=0,
                application_status="NOT_APPLIED",
            )
        )
        db.commit()


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


def test_chatbot_uses_mocked_solar_and_only_selected_policy(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The endpoint is stateless and never reaches the real Solar network."""

    token, _user_id = _signup(client, email="chatbot-user@example.com")
    selected_policy_id = _seed_policy(
        external_id="chatbot-selected",
        title="선택한 청년 주거 정책",
        application_end_date=date(2026, 12, 31),
        with_condition=True,
    )
    _seed_policy(
        external_id="chatbot-other",
        title="다른 정책의 비밀 제목",
        application_end_date=date(2026, 11, 30),
    )
    captured_messages: list[dict[str, str]] = []

    async def fake_complete(
        _solar_client: SolarClient,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 2_048,
    ) -> str:
        del temperature, max_tokens
        captured_messages.extend(dict(message) for message in messages)
        return "선택한 정책만 사용한 모의 답변입니다."

    monkeypatch.setattr(SolarClient, "complete", fake_complete)
    response = client.post(
        f"/api/v1/policies/{selected_policy_id}/questions",
        headers=_headers(token),
        json={"question": "지원 대상과 신청 방법을 알려주세요."},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "answer": "선택한 정책만 사용한 모의 답변입니다.",
        "suggested_questions": _SUGGESTED_QUESTIONS,
    }
    assert [message["role"] for message in captured_messages] == [
        "system",
        "user",
    ]
    user_prompt = captured_messages[1]["content"]
    assert "선택한 청년 주거 정책" in user_prompt
    assert "만 19세부터 34세" in user_prompt
    assert "지원 대상과 신청 방법을 알려주세요." in user_prompt
    assert "다른 정책의 비밀 제목" not in user_prompt


def test_chatbot_maps_solar_failure_to_503(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token, _user_id = _signup(client, email="chatbot-error@example.com")
    policy_id = _seed_policy(
        external_id="chatbot-error-policy",
        title="AI 장애 테스트 정책",
        application_end_date=date(2026, 12, 31),
    )

    async def fail_complete(
        _solar_client: SolarClient,
        _messages: Sequence[Mapping[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 2_048,
    ) -> str:
        del temperature, max_tokens
        raise SolarClientError("mocked upstream failure")

    monkeypatch.setattr(SolarClient, "complete", fail_complete)
    response = client.post(
        f"/api/v1/policies/{policy_id}/questions",
        headers=_headers(token),
        json={"question": "이 정책을 설명해 주세요."},
    )

    assert response.status_code == 503, response.text
    assert response.json() == {
        "code": "EXTERNAL_SERVICE_UNAVAILABLE",
        "detail": "AI 답변 서비스를 현재 사용할 수 없습니다.",
    }


def test_chatbot_missing_policy_returns_404_without_solar(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token, _user_id = _signup(client, email="chatbot-missing@example.com")
    solar_called = False

    async def forbidden_complete(
        _solar_client: SolarClient,
        _messages: Sequence[Mapping[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 2_048,
    ) -> str:
        nonlocal solar_called
        del temperature, max_tokens
        solar_called = True
        return "호출되면 안 됩니다."

    monkeypatch.setattr(SolarClient, "complete", forbidden_complete)
    response = client.post(
        "/api/v1/policies/999999/questions",
        headers=_headers(token),
        json={"question": "없는 정책인가요?"},
    )

    assert response.status_code == 404, response.text
    assert response.json() == {
        "code": "NOT_FOUND",
        "detail": "정책을 찾을 수 없습니다.",
    }
    assert solar_called is False


def test_notification_settings_get_and_patch(client: TestClient) -> None:
    token, user_id = _signup(client)
    headers = _headers(token)

    get_response = client.get(
        "/api/v1/users/me/notification-settings",
        headers=headers,
    )
    assert get_response.status_code == 200, get_response.text
    initial = get_response.json()
    assert set(initial) == _SETTING_KEYS
    assert initial == {
        "user_id": user_id,
        "notification_enabled": True,
        "deadline_d7_enabled": True,
        "deadline_d3_enabled": True,
        "deadline_d0_enabled": True,
        "email_enabled": True,
        "push_enabled": True,
        "updated_at": initial["updated_at"],
    }
    assert isinstance(initial["updated_at"], str)

    patch_response = client.patch(
        "/api/v1/users/me/notification-settings",
        headers=headers,
        json={
            "notification_enabled": True,
            "deadline_d7_enabled": False,
            "deadline_d3_enabled": True,
            "deadline_d0_enabled": False,
            "email_enabled": False,
            "push_enabled": True,
        },
    )
    assert patch_response.status_code == 200, patch_response.text
    updated = patch_response.json()
    assert set(updated) == _SETTING_KEYS
    assert updated == {
        "user_id": user_id,
        "notification_enabled": True,
        "deadline_d7_enabled": False,
        "deadline_d3_enabled": True,
        "deadline_d0_enabled": False,
        "email_enabled": False,
        "push_enabled": True,
        "updated_at": updated["updated_at"],
    }

    second_get = client.get(
        "/api/v1/users/me/notification-settings",
        headers=headers,
    )
    assert second_get.status_code == 200, second_get.text
    assert second_get.json() == updated


def test_deadline_generation_feed_dedup_and_read_flow(
    client: TestClient,
) -> None:
    fixed_now = datetime(2026, 7, 29, 12, 30, tzinfo=UTC)
    token, user_id = _signup(client, email="deadline-user@example.com")
    headers = _headers(token)
    settings_response = client.get(
        "/api/v1/users/me/notification-settings",
        headers=headers,
    )
    assert settings_response.status_code == 200, settings_response.text

    expected: dict[str, tuple[int, str, str]] = {}
    for days_left, event_type in (
        (7, "DEADLINE_D7"),
        (3, "DEADLINE_D3"),
        (0, "DEADLINE_D0"),
    ):
        title = f"마감 {days_left}일 정책"
        policy_id = _seed_policy(
            external_id=f"deadline-{days_left}",
            title=title,
            application_end_date=fixed_now.date() + timedelta(days=days_left),
        )
        _bookmark_policy(user_id=user_id, policy_id=policy_id, bookmarked=True)
        if days_left == 0:
            expected_title = f"[마감일] {title}"
            expected_body = f"관심 정책 '{title}'의 신청 마감일입니다."
        else:
            expected_title = f"[D-{days_left}] {title}"
            expected_body = f"관심 정책 '{title}'의 신청 마감까지 {days_left}일 남았습니다."
        expected[event_type] = (policy_id, expected_title, expected_body)

    not_bookmarked_id = _seed_policy(
        external_id="deadline-not-bookmarked",
        title="관심 아님",
        application_end_date=fixed_now.date() + timedelta(days=7),
    )
    _bookmark_policy(
        user_id=user_id,
        policy_id=not_bookmarked_id,
        bookmarked=False,
    )
    ongoing_id = _seed_policy(
        external_id="deadline-ongoing",
        title="상시 정책",
        application_end_date=fixed_now.date() + timedelta(days=7),
        is_ongoing=True,
    )
    _bookmark_policy(user_id=user_id, policy_id=ongoing_id, bookmarked=True)
    inactive_id = _seed_policy(
        external_id="deadline-inactive",
        title="비활성 정책",
        application_end_date=fixed_now.date() + timedelta(days=7),
        is_active=False,
    )
    _bookmark_policy(user_id=user_id, policy_id=inactive_id, bookmarked=True)
    other_day_id = _seed_policy(
        external_id="deadline-d1",
        title="D-1 정책",
        application_end_date=fixed_now.date() + timedelta(days=1),
    )
    _bookmark_policy(user_id=user_id, policy_id=other_day_id, bookmarked=True)

    with SessionLocal() as db:
        created = create_due_deadline_notifications(db, as_of=fixed_now)
        assert len(created) == 3
        assert {_enum_value(item.notification_type) for item in created} == set(expected)
        # KST 9시를 의미하는 naive 값 — 이 fixture는 자정 경계가 아니라 리터럴 값 자체는 그대로다.
        assert all(item.scheduled_at == datetime(2026, 7, 29, 9, 0) for item in created)
        assert all(_enum_value(item.send_status) == "PENDING" for item in created)

    with SessionLocal() as db:
        duplicate_attempt = create_due_deadline_notifications(
            db,
            as_of=fixed_now,
        )
        assert duplicate_attempt == []

    feed_response = client.get(
        "/api/v1/users/me/notifications?unread_only=false&limit=50",
        headers=headers,
    )
    assert feed_response.status_code == 200, feed_response.text
    feed = feed_response.json()
    assert len(feed) == 3
    assert {item["notification_type"] for item in feed} == set(expected)
    for item in feed:
        assert set(item) == _NOTIFICATION_KEYS
        expected_policy_id, expected_title, expected_body = expected[item["notification_type"]]
        assert item == {
            "id": item["id"],
            "policy_id": expected_policy_id,
            "notification_type": item["notification_type"],
            "title": expected_title,
            "body": expected_body,
            "scheduled_at": "2026-07-29T09:00:00",
            "sent_at": None,
            "read_at": None,
            "send_status": "PENDING",
        }

    target = next(item for item in feed if item["notification_type"] == "DEADLINE_D3")
    other_token, _other_user_id = _signup(
        client,
        email="other-notification-user@example.com",
    )
    forbidden_read = client.patch(
        f"/api/v1/notifications/{target['id']}/read",
        headers=_headers(other_token),
    )
    assert forbidden_read.status_code == 404, forbidden_read.text
    assert forbidden_read.json() == {
        "code": "NOT_FOUND",
        "detail": "알림을 찾을 수 없습니다.",
    }

    read_response = client.patch(
        f"/api/v1/notifications/{target['id']}/read",
        headers=headers,
    )
    assert read_response.status_code == 200, read_response.text
    read_item = read_response.json()
    assert set(read_item) == _NOTIFICATION_KEYS
    assert read_item["id"] == target["id"]
    assert read_item["notification_type"] == "DEADLINE_D3"
    assert isinstance(read_item["read_at"], str)
    assert read_item["send_status"] == "PENDING"

    unread_response = client.get(
        "/api/v1/users/me/notifications?unread_only=true&limit=100",
        headers=headers,
    )
    assert unread_response.status_code == 200, unread_response.text
    unread = unread_response.json()
    assert len(unread) == 2
    assert target["id"] not in {item["id"] for item in unread}
    assert all(item["read_at"] is None for item in unread)


def test_deadline_day_boundary_uses_kst_not_utc(client: TestClient) -> None:
    """UTC 오후 8시(=KST 다음날 새벽 5시)에도 KST 기준 날짜로 D-day가 잡혀야 한다.

    예전 UTC 기준 코드였다면 current.date()가 07-29로 계산되어 D-1로 어긋났을 케이스.
    """

    as_of = datetime(2026, 7, 29, 20, 0, tzinfo=UTC)  # KST로는 2026-07-30 05:00
    token, user_id = _signup(client, email="deadline-boundary-user@example.com")
    headers = _headers(token)
    settings_response = client.get(
        "/api/v1/users/me/notification-settings",
        headers=headers,
    )
    assert settings_response.status_code == 200, settings_response.text

    policy_id = _seed_policy(
        external_id="deadline-boundary-dday",
        title="자정 경계 D-day 정책",
        application_end_date=date(2026, 7, 30),
    )
    _bookmark_policy(user_id=user_id, policy_id=policy_id, bookmarked=True)

    with SessionLocal() as db:
        created = create_due_deadline_notifications(db, as_of=as_of)
        assert len(created) == 1
        assert _enum_value(created[0].notification_type) == "DEADLINE_D0"
        assert created[0].scheduled_at == datetime(2026, 7, 30, 9, 0)


def test_deadline_notification_job_is_registered(client: TestClient) -> None:
    """main.py의 lifespan이 등록하는 APScheduler cron 잡이 실제로 존재하는지 확인한다."""

    job_ids = {job.id for job in main.scheduler.get_jobs()}
    assert "deadline_notifications" in job_ids


def test_run_deadline_check_endpoint_creates_and_dedups(client: TestClient) -> None:
    """POST .../run-deadline-check는 그날 마감 알림을 한 번만 만들고 재호출 시 dedup된다."""

    today = datetime.now(KST).date()
    token, user_id = _signup(client, email="deadline-endpoint-user@example.com")
    headers = _headers(token)
    settings_response = client.get(
        "/api/v1/users/me/notification-settings",
        headers=headers,
    )
    assert settings_response.status_code == 200, settings_response.text

    policy_id = _seed_policy(
        external_id="deadline-endpoint-dday",
        title="엔드포인트 마감 정책",
        application_end_date=today,
    )
    _bookmark_policy(user_id=user_id, policy_id=policy_id, bookmarked=True)

    first_response = client.post(
        "/api/v1/users/me/notifications/run-deadline-check",
        headers=headers,
    )
    assert first_response.status_code == 200, first_response.text
    first_result = first_response.json()
    assert len(first_result) == 1
    assert first_result[0]["policy_id"] == policy_id
    assert first_result[0]["notification_type"] == "DEADLINE_D0"

    second_response = client.post(
        "/api/v1/users/me/notifications/run-deadline-check",
        headers=headers,
    )
    assert second_response.status_code == 200, second_response.text
    assert second_response.json() == []


@pytest.mark.parametrize(
    ("settings_patch", "days_left"),
    [
        ({"notification_enabled": False}, 7),
        ({"deadline_d3_enabled": False}, 3),
        ({"email_enabled": False, "push_enabled": False}, 0),
    ],
)
def test_deadline_generation_respects_notification_toggles(
    client: TestClient,
    settings_patch: dict[str, bool],
    days_left: int,
) -> None:
    fixed_now = datetime(2026, 7, 29, 12, 30, tzinfo=UTC)
    token, user_id = _signup(
        client,
        email=f"toggle-{days_left}-{len(settings_patch)}@example.com",
    )
    headers = _headers(token)
    settings_response = client.patch(
        "/api/v1/users/me/notification-settings",
        headers=headers,
        json=settings_patch,
    )
    assert settings_response.status_code == 200, settings_response.text
    for key, value in settings_patch.items():
        assert settings_response.json()[key] is value

    policy_id = _seed_policy(
        external_id=f"toggle-policy-{days_left}",
        title=f"토글 테스트 D-{days_left}",
        application_end_date=fixed_now.date() + timedelta(days=days_left),
    )
    _bookmark_policy(user_id=user_id, policy_id=policy_id, bookmarked=True)

    with SessionLocal() as db:
        assert create_due_deadline_notifications(db, as_of=fixed_now) == []

    feed_response = client.get(
        "/api/v1/users/me/notifications",
        headers=headers,
    )
    assert feed_response.status_code == 200, feed_response.text
    assert feed_response.json() == []


@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        (
            "POST",
            "/api/v1/policies/1/questions",
            {"question": "인증이 필요한가요?"},
        ),
        ("GET", "/api/v1/users/me/notification-settings", None),
        ("PATCH", "/api/v1/users/me/notification-settings", {}),
        ("GET", "/api/v1/users/me/notifications", None),
        ("PATCH", "/api/v1/notifications/1/read", None),
    ],
)
def test_chatbot_and_notification_routes_require_authentication(
    client: TestClient,
    method: str,
    path: str,
    json_body: dict[str, object] | None,
) -> None:
    request_kwargs = {"json": json_body} if json_body is not None else {}
    response = client.request(method, path, **request_kwargs)
    assert response.status_code == 401, response.text
    assert response.json() == {
        "code": "AUTHENTICATION_FAILED",
        "detail": "로그인이 필요합니다.",
    }


def test_health_is_public_and_strict(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}
