"""Category, policy list/detail, match, and bookmark routes."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, DbSession
from app.crud import categories as category_crud
from app.crud import user_policies as state_crud
from app.schemas.policy import (
    PolicyBenefitResponse,
    PolicyBookmarkResponse,
    PolicyCategoryResponse,
    PolicyConditionResponse,
    PolicyConditionResultResponse,
    PolicyDetailResponse,
    PolicyDocumentResponse,
    PolicyListResponse,
    PolicyMatchDetailResponse,
    PolicyMatchResponse,
    PolicySummaryResponse,
)
from app.schemas.user import (
    CategoryAnswerResponse,
    CategoryAnswersUpdate,
    CategoryQuestionResponse,
    CategoryResponse,
)
from app.services import policy_service

router = APIRouter(tags=["policies"])


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(db: DbSession) -> list[CategoryResponse]:
    """Return active policy categories in display order."""

    return [
        CategoryResponse(
            id=category.id,
            code=category.code,
            name=category.name,
            description=category.description,
            display_order=category.display_order,
            is_active=category.is_active,
            questions=[],
        )
        for category in category_crud.list_categories(db)
    ]


@router.get(
    "/categories/{category_id}/questions",
    response_model=list[CategoryQuestionResponse],
)
def list_category_questions(
    category_id: int,
    db: DbSession,
) -> list[CategoryQuestionResponse]:
    """Return category-specific onboarding questions."""

    category = category_crud.get_category(db, category_id)
    if category is None:
        from app.services.errors import NotFoundError

        raise NotFoundError("카테고리를 찾을 수 없습니다.")
    return [
        CategoryQuestionResponse.model_validate(question)
        for question in category_crud.list_category_questions(db, category_id)
    ]


@router.put(
    "/categories/{category_id}/answers",
    response_model=list[CategoryAnswerResponse],
)
def save_category_answers(
    category_id: int,
    payload: CategoryAnswersUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> list[CategoryAnswerResponse]:
    """Save reusable category answers for the current user."""

    records = category_crud.upsert_user_category_answers(
        db,
        user_id=current_user.id,
        category_id=category_id,
        answers=[answer.model_dump() for answer in payload.answers],
    )
    return [CategoryAnswerResponse.model_validate(record) for record in records]


@router.get("/policies", response_model=PolicyListResponse)
def list_policies(
    db: DbSession,
    current_user: CurrentUser,
    category_code: str | None = None,
    eligibility_status: str | None = Query(
        default=None,
        pattern="^(ELIGIBLE|NEEDS_REVIEW)$",
    ),
    sort: str = Query(
        default="recommendation",
        pattern="^(recommendation|latest|deadline)$",
    ),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None, min_length=1, max_length=100),
) -> PolicyListResponse:
    """Return user-evaluated policy cards."""

    result = policy_service.list_evaluated_policies(
        db,
        user_id=current_user.id,
        category_code=category_code,
        eligibility_status=eligibility_status,
        sort=sort,
        keyword=keyword,
        page=page,
        size=size,
    )
    return PolicyListResponse(
        items=[_policy_summary(item, current_user.id, db) for item in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
    )


@router.get(
    "/users/me/recommendations",
    response_model=list[PolicySummaryResponse],
)
def list_recommendations(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[PolicySummaryResponse]:
    """Return category-independent recommendations in match order."""

    return [
        _policy_summary(item, current_user.id, db)
        for item in policy_service.list_recommendations(
            db,
            user_id=current_user.id,
            limit=limit,
        )
    ]


@router.get(
    "/policies/{policy_id}",
    response_model=PolicyDetailResponse,
)
def get_policy_detail(
    policy_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> PolicyDetailResponse:
    """Return policy source details and confirmed condition/document data."""

    evaluated = policy_service.evaluate_policy_for_user(
        db,
        user_id=current_user.id,
        policy_id=policy_id,
    )
    summary = _policy_summary(evaluated, current_user.id, db)
    policy = evaluated.bundle.policy
    return PolicyDetailResponse(
        **summary.model_dump(),
        description=policy.description,
        support_target_text=policy.support_target_text,
        support_content_text=policy.support_content_text,
        application_method=policy.application_method,
        application_url=policy.application_url,
        contact=policy.contact,
        conditions=[
            PolicyConditionResponse.model_validate(condition)
            for condition in evaluated.bundle.conditions
        ],
        benefits=[
            PolicyBenefitResponse.model_validate(benefit) for benefit in evaluated.bundle.benefits
        ],
        documents=[
            PolicyDocumentResponse.model_validate(document)
            for document in evaluated.bundle.documents
        ],
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@router.get(
    "/policies/{policy_id}/match",
    response_model=PolicyMatchDetailResponse,
)
def get_policy_match(
    policy_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> PolicyMatchDetailResponse:
    """Return the condition-level three-state evaluation."""

    evaluated = policy_service.evaluate_policy_for_user(
        db,
        user_id=current_user.id,
        policy_id=policy_id,
    )
    match = evaluated.match
    conditions = [
        PolicyConditionResultResponse(
            condition_id=result.condition_id or condition.id,
            condition_key=result.condition_key,
            description=condition.description,
            status=result.status,
            actual_value_json={"value": _json_value(result.actual_value)},
            reason=result.reason,
            check_mode=condition.check_mode,
            evaluated_at=match.evaluated_at,
        )
        for condition, result in zip(
            evaluated.bundle.conditions,
            evaluated.evaluation.condition_results,
            strict=True,
        )
    ]
    return PolicyMatchDetailResponse(
        **_match_response(evaluated).model_dump(),
        conditions=conditions,
    )


@router.post(
    "/policies/{policy_id}/bookmark",
    response_model=PolicyBookmarkResponse,
    status_code=status.HTTP_201_CREATED,
)
def bookmark_policy(
    policy_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> PolicyBookmarkResponse:
    """Add a policy to the interest list."""

    policy_service.get_policy_entity(db, policy_id)
    state = state_crud.set_bookmark(
        db,
        user_id=current_user.id,
        policy_id=policy_id,
        bookmarked=True,
    )
    return PolicyBookmarkResponse(
        policy_id=policy_id,
        is_bookmarked=True,
        bookmarked_at=state.bookmarked_at,
    )


@router.delete(
    "/policies/{policy_id}/bookmark",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_policy_bookmark(
    policy_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> Response:
    """Remove a policy from the interest list."""

    policy_service.get_policy_entity(db, policy_id)
    state_crud.set_bookmark(
        db,
        user_id=current_user.id,
        policy_id=policy_id,
        bookmarked=False,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _policy_summary(
    evaluated: policy_service.EvaluatedPolicy,
    user_id: int,
    db: DbSession,
) -> PolicySummaryResponse:
    policy = evaluated.bundle.policy
    state = state_crud.get_user_policy_state(
        db,
        user_id=user_id,
        policy_id=policy.id,
    )
    categories = [
        PolicyCategoryResponse(
            id=category.id,
            code=category.code,
            name=category.name,
            is_primary=index == 0,
        )
        for index, category in enumerate(evaluated.bundle.categories)
    ]
    return PolicySummaryResponse(
        id=policy.id,
        source=policy.source,
        title=policy.title,
        summary=policy.summary,
        provider_name=policy.provider_name,
        application_start_date=policy.application_start_date,
        application_end_date=policy.application_end_date,
        is_ongoing=policy.is_ongoing,
        published_date=policy.published_date,
        status=policy.status,
        subcategory=policy.subcategory,
        region_scope=policy.region_scope,
        categories=categories,
        card_status=evaluated.evaluation.status,
        match_score=evaluated.match.match_score,
        estimated_benefit_amount=evaluated.estimated_benefit_amount,
        max_benefit_amount=evaluated.estimated_benefit_amount,
        days_until_deadline=_days_until(policy.application_end_date),
        is_bookmarked=bool(state and state.is_bookmarked),
    )


def _match_response(
    evaluated: policy_service.EvaluatedPolicy,
) -> PolicyMatchResponse:
    match = evaluated.match
    return PolicyMatchResponse(
        id=match.id,
        user_id=match.user_id,
        policy_id=match.policy_id,
        card_status=evaluated.evaluation.status,
        match_score=match.match_score,
        satisfied_condition_count=match.satisfied_condition_count,
        review_condition_count=match.review_condition_count,
        failed_condition_count=match.failed_condition_count,
        total_condition_count=match.total_condition_count,
        estimated_benefit_amount=match.estimated_benefit_amount,
        engine_version=match.engine_version,
        evaluated_at=match.evaluated_at,
    )


def _days_until(end_date: date | None) -> int | None:
    if end_date is None:
        return None
    return (end_date - date.today()).days


def _json_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value
