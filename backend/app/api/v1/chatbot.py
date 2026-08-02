"""Stateless, policy-scoped AI Q&A route."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.chatbot import PolicyQuestionRequest, PolicyQuestionResponse
from app.services.chatbot_service import SUGGESTED_QUESTIONS, ask_policy_question

router = APIRouter(prefix="/policies", tags=["chatbot"])


@router.post(
    "/{policy_id}/questions",
    response_model=PolicyQuestionResponse,
)
async def ask_about_policy(
    policy_id: int,
    payload: PolicyQuestionRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> PolicyQuestionResponse:
    """Answer one question without accepting or persisting chat history."""

    del current_user  # Authentication gates this feature; no history is stored.
    answer = await ask_policy_question(
        db,
        policy_id=policy_id,
        question=payload.question,
    )
    return PolicyQuestionResponse(
        answer=answer,
        suggested_questions=SUGGESTED_QUESTIONS,
    )
