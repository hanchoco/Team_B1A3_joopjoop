"""Stateless, current-policy-only AI Q&A orchestration."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.crud import policies as policy_crud
from app.services.ai.solar_client import (
    SolarClientError,
    answer_policy_question,
)
from app.services.errors import ExternalServiceError, NotFoundError

SUGGESTED_QUESTIONS = [
    "제가 이 정책에 지원할 수 있나요?",
    "필요한 서류는 무엇인가요?",
    "소득 기준은 어떻게 계산하나요?",
    "신청 절차가 궁금합니다.",
]


async def ask_policy_question(
    db: Session,
    *,
    policy_id: int,
    question: str,
) -> str:
    """Ask Solar using only the policy currently selected by the user."""

    bundle = policy_crud.get_policy_bundle(db, policy_id)
    if bundle is None:
        raise NotFoundError("정책을 찾을 수 없습니다.")
    policy = bundle.policy
    context = {
        "external_id": policy.external_id,
        "title": policy.title,
        "summary": policy.summary,
        "description": policy.description,
        "support_target_text": policy.support_target_text,
        "support_content_text": policy.support_content_text,
        "application_method": policy.application_method,
        "application_start_date": _stringify(policy.application_start_date),
        "application_end_date": _stringify(policy.application_end_date),
        "is_ongoing": policy.is_ongoing,
        "provider_name": policy.provider_name,
        "application_url": policy.application_url,
        "contact": policy.contact,
        "original_text": policy.original_text,
        "conditions": [
            {
                "condition_key": condition.condition_key,
                "operator": str(condition.operator).split(".")[-1],
                "expected_value_json": condition.expected_value_json,
                "check_mode": str(condition.check_mode).split(".")[-1],
                "description": condition.description,
            }
            for condition in bundle.conditions
        ],
    }
    try:
        return await answer_policy_question(question, context)
    except SolarClientError as exc:
        raise ExternalServiceError("AI 답변 서비스를 현재 사용할 수 없습니다.") from exc


def _stringify(value: object) -> object:
    if isinstance(value, (date, datetime, Decimal)):
        return str(value)
    return value
