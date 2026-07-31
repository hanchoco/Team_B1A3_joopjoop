"""Preparation checklist and My Policies orchestration."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.crud import policies as policy_crud
from app.crud import user_policies as state_crud
from app.models.user_document_progress import UserDocumentProgress
from app.models.user_policy import (
    UserPolicyConditionResult,
    UserPolicyMatch,
    UserPolicyState,
)
from app.services.errors import NotFoundError
from app.services.policy_service import evaluate_policy_for_user


@dataclass(slots=True)
class ChecklistBundle:
    """Everything required to render the preparation page."""

    state: UserPolicyState
    policy_bundle: policy_crud.PolicyBundle
    match: UserPolicyMatch
    condition_results: list[UserPolicyConditionResult]
    document_progress: list[UserDocumentProgress]


@dataclass(slots=True)
class UserPolicyItem:
    """A My Policies list row."""

    state: UserPolicyState
    policy: object
    match: UserPolicyMatch | None
    category_code: str | None


def start_checklist(
    db: Session,
    *,
    user_id: int,
    policy_id: int,
) -> ChecklistBundle:
    """Evaluate the policy and create resumable checklist state."""

    evaluated = evaluate_policy_for_user(db, user_id=user_id, policy_id=policy_id)
    state = state_crud.start_preparation(
        db,
        user_id=user_id,
        policy_id=policy_id,
    )
    return _assemble_checklist(
        db,
        user_id=user_id,
        state=state,
        bundle=evaluated.bundle,
        match=evaluated.match,
    )


def get_checklist(
    db: Session,
    *,
    user_id: int,
    state_id: int,
) -> ChecklistBundle:
    """Return a resumable checklist owned by the current user."""

    state = state_crud.get_user_policy_state_by_id(
        db,
        state_id=state_id,
        user_id=user_id,
    )
    if state is None:
        raise NotFoundError("준비 중인 정책을 찾을 수 없습니다.")
    bundle = policy_crud.get_policy_bundle(db, state.policy_id)
    match = state_crud.get_policy_match(
        db,
        user_id=user_id,
        policy_id=state.policy_id,
    )
    if bundle is None or match is None:
        raise NotFoundError("정책 또는 매칭 결과를 찾을 수 없습니다.")
    return _assemble_checklist(
        db,
        user_id=user_id,
        state=state,
        bundle=bundle,
        match=match,
    )


def update_document(
    db: Session,
    *,
    user_id: int,
    state_id: int,
    document_id: int,
    preparation_status: str,
    is_checked: bool,
    note: str | None,
) -> ChecklistBundle:
    """Update one document and return the refreshed checklist."""

    try:
        state_crud.update_document_progress(
            db,
            user_id=user_id,
            state_id=state_id,
            document_id=document_id,
            preparation_status=preparation_status,
            is_checked=is_checked,
            note=note,
        )
    except LookupError as exc:
        raise NotFoundError(str(exc)) from exc
    return get_checklist(db, user_id=user_id, state_id=state_id)


def confirm_condition(
    db: Session,
    *,
    user_id: int,
    state_id: int,
    condition_id: int,
    confirmed: bool,
) -> ChecklistBundle:
    """Save the user's confirmation and return refreshed progress."""

    try:
        state_crud.confirm_condition(
            db,
            user_id=user_id,
            state_id=state_id,
            condition_id=condition_id,
            confirmed=confirmed,
        )
    except LookupError as exc:
        raise NotFoundError(str(exc)) from exc
    return get_checklist(db, user_id=user_id, state_id=state_id)


def record_application(
    db: Session,
    *,
    user_id: int,
    policy_id: int,
    application_date: date,
    application_status: str,
    application_note: str | None,
) -> UserPolicyState:
    """Move a policy into the user's application history."""

    if policy_crud.get_policy(db, policy_id) is None:
        raise NotFoundError("정책을 찾을 수 없습니다.")
    return state_crud.complete_application(
        db,
        user_id=user_id,
        policy_id=policy_id,
        application_date=application_date,
        application_status=application_status,
        application_note=application_note,
    )


def list_my_policies(
    db: Session,
    *,
    user_id: int,
    tab: str | None,
    sort: str,
) -> list[UserPolicyItem]:
    """Return My Page policy rows with cached match metadata."""

    states = state_crud.list_user_policy_states(
        db,
        user_id=user_id,
        tab=tab,
        sort=sort,
    )
    policies = {
        policy.id: policy
        for policy in policy_crud.list_policies_by_ids(
            db,
            [state.policy_id for state in states],
        )
    }
    items: list[UserPolicyItem] = []
    for state in states:
        if state.policy_id not in policies:
            continue
        categories = policy_crud.list_policy_categories(db, state.policy_id)
        items.append(
            UserPolicyItem(
                state=state,
                policy=policies[state.policy_id],
                match=state_crud.get_policy_match(
                    db,
                    user_id=user_id,
                    policy_id=state.policy_id,
                ),
                category_code=(categories[0].code.value if categories else None),
            )
        )
    return items


def _assemble_checklist(
    db: Session,
    *,
    user_id: int,
    state: UserPolicyState,
    bundle: policy_crud.PolicyBundle,
    match: UserPolicyMatch,
) -> ChecklistBundle:
    del user_id  # ownership was checked by the caller/CRUD query.
    return ChecklistBundle(
        state=state,
        policy_bundle=bundle,
        match=match,
        condition_results=state_crud.list_condition_results(db, match.id),
        document_progress=state_crud.list_document_progress(db, state.id),
    )
