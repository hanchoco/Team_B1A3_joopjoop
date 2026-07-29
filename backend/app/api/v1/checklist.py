"""Preparation checklist and My Policies routes."""

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.checklist import (
    ApplicationCreate,
    ChecklistConditionItem,
    ChecklistDocumentItem,
    ChecklistResponse,
    ConditionConfirmationUpdate,
    DocumentProgressUpdate,
    UserPolicyItemResponse,
)
from app.services import checklist_service

router = APIRouter(tags=["checklist"])


@router.post(
    "/policies/{policy_id}/preparation",
    response_model=ChecklistResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_preparation(
    policy_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> ChecklistResponse:
    """Start or resume the policy's persistent application checklist."""

    bundle = checklist_service.start_checklist(
        db,
        user_id=current_user.id,
        policy_id=policy_id,
    )
    return _checklist_response(bundle)


@router.get(
    "/preparations/{state_id}",
    response_model=ChecklistResponse,
)
def get_preparation(
    state_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> ChecklistResponse:
    """Resume a previously started checklist."""

    return _checklist_response(
        checklist_service.get_checklist(
            db,
            user_id=current_user.id,
            state_id=state_id,
        )
    )


@router.patch(
    "/preparations/{state_id}/documents/{document_id}",
    response_model=ChecklistResponse,
)
def update_preparation_document(
    state_id: int,
    document_id: int,
    payload: DocumentProgressUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ChecklistResponse:
    """Update a required document and the cached checklist percentage."""

    bundle = checklist_service.update_document(
        db,
        user_id=current_user.id,
        state_id=state_id,
        document_id=document_id,
        preparation_status=payload.preparation_status,
        is_checked=payload.is_checked,
        note=payload.note,
    )
    return _checklist_response(bundle)


@router.patch(
    "/preparations/{state_id}/conditions/{condition_id}",
    response_model=ChecklistResponse,
)
def confirm_preparation_condition(
    state_id: int,
    condition_id: int,
    payload: ConditionConfirmationUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ChecklistResponse:
    """Confirm a manual/document condition."""

    bundle = checklist_service.confirm_condition(
        db,
        user_id=current_user.id,
        state_id=state_id,
        condition_id=condition_id,
        confirmed=payload.confirmed,
    )
    return _checklist_response(bundle)


@router.post(
    "/policies/{policy_id}/applications",
    response_model=UserPolicyItemResponse,
)
def record_policy_application(
    policy_id: int,
    payload: ApplicationCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> UserPolicyItemResponse:
    """Record a submitted policy application."""

    state = checklist_service.record_application(
        db,
        user_id=current_user.id,
        policy_id=policy_id,
        application_date=payload.application_date,
        application_status=payload.application_status,
        application_note=payload.application_note,
    )
    items = checklist_service.list_my_policies(
        db,
        user_id=current_user.id,
        tab="applied",
        sort="latest",
    )
    item = next(item for item in items if item.state.id == state.id)
    return _user_policy_response(item)


@router.get(
    "/users/me/policies",
    response_model=list[UserPolicyItemResponse],
)
def list_my_policies(
    db: DbSession,
    current_user: CurrentUser,
    tab: str | None = Query(
        default=None,
        pattern="^(bookmarked|preparing|applied)$",
    ),
    sort: str = Query(
        default="latest",
        pattern="^(recommendation|latest|deadline)$",
    ),
) -> list[UserPolicyItemResponse]:
    """List interest, preparation, and application states."""

    return [
        _user_policy_response(item)
        for item in checklist_service.list_my_policies(
            db,
            user_id=current_user.id,
            tab=tab,
            sort=sort,
        )
    ]


def _checklist_response(
    bundle: checklist_service.ChecklistBundle,
) -> ChecklistResponse:
    conditions_by_id = {condition.id: condition for condition in bundle.policy_bundle.conditions}
    documents_by_id = {document.id: document for document in bundle.policy_bundle.documents}
    conditions = [
        ChecklistConditionItem(
            condition_id=result.condition_id,
            condition_key=conditions_by_id[result.condition_id].condition_key,
            description=conditions_by_id[result.condition_id].description,
            result_status=_enum_value(result.result_status),
            reason=result.reason or "",
            is_user_confirmed=result.is_user_confirmed,
            confirmed_at=result.confirmed_at,
        )
        for result in bundle.condition_results
        if result.condition_id in conditions_by_id
    ]
    documents = [
        ChecklistDocumentItem(
            document_id=progress.document_id,
            document_code=documents_by_id[progress.document_id].document_code,
            document_name=documents_by_id[progress.document_id].document_name,
            required_reason=documents_by_id[progress.document_id].required_reason,
            issuing_organization=documents_by_id[progress.document_id].issuing_organization,
            issuing_method=documents_by_id[progress.document_id].issuing_method,
            issuing_url=documents_by_id[progress.document_id].issuing_url,
            submission_format=documents_by_id[progress.document_id].submission_format,
            is_required=documents_by_id[progress.document_id].is_required,
            preparation_status=_enum_value(progress.preparation_status),
            is_checked=progress.is_checked,
            checked_at=progress.checked_at,
            note=progress.note,
        )
        for progress in bundle.document_progress
        if progress.document_id in documents_by_id
    ]
    return ChecklistResponse(
        state_id=bundle.state.id,
        policy_id=bundle.state.policy_id,
        policy_title=bundle.policy_bundle.policy.title,
        preparation_status=_enum_value(bundle.state.preparation_status),
        progress_percent=bundle.state.progress_percent,
        conditions=conditions,
        documents=documents,
    )


def _user_policy_response(
    item: checklist_service.UserPolicyItem,
) -> UserPolicyItemResponse:
    policy = item.policy
    return UserPolicyItemResponse(
        state_id=item.state.id,
        policy_id=item.state.policy_id,
        title=policy.title,
        summary=policy.summary,
        application_end_date=policy.application_end_date,
        is_bookmarked=item.state.is_bookmarked,
        preparation_status=_enum_value(item.state.preparation_status),
        progress_percent=item.state.progress_percent,
        application_status=_enum_value(item.state.application_status),
        application_date=item.state.application_date,
        match_score=item.match.match_score if item.match else None,
        eligibility_status=(_enum_value(item.match.eligibility_status) if item.match else None),
        updated_at=item.state.updated_at,
    )


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))
