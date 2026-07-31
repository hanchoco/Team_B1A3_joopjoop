"""User-policy match, bookmark, preparation, and application persistence."""

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.policy import Policy
from app.models.policy_document import PolicyDocument
from app.models.user_document_progress import UserDocumentProgress
from app.models.user_policy import (
    UserPolicyConditionResult,
    UserPolicyMatch,
    UserPolicyState,
)


def get_policy_match(
    db: Session,
    *,
    user_id: int,
    policy_id: int,
) -> UserPolicyMatch | None:
    """Return a cached user-policy evaluation."""

    statement = select(UserPolicyMatch).where(
        UserPolicyMatch.user_id == user_id,
        UserPolicyMatch.policy_id == policy_id,
    )
    return db.scalar(statement)


def list_condition_results(
    db: Session,
    match_id: int,
) -> list[UserPolicyConditionResult]:
    """Return condition-level results for a cached match."""

    statement = (
        select(UserPolicyConditionResult)
        .where(UserPolicyConditionResult.match_id == match_id)
        .order_by(UserPolicyConditionResult.condition_id.asc())
    )
    return list(db.scalars(statement).all())


def upsert_policy_match(
    db: Session,
    *,
    user_id: int,
    policy_id: int,
    eligibility_status: str,
    match_score: Decimal,
    satisfied_condition_count: int,
    review_condition_count: int,
    failed_condition_count: int,
    total_condition_count: int,
    estimated_benefit_amount: Decimal | None,
    engine_version: str,
    condition_results: Sequence[Mapping[str, object]],
) -> UserPolicyMatch:
    """Store a policy-level match and its condition-level explanations."""

    match = get_policy_match(db, user_id=user_id, policy_id=policy_id)
    now = datetime.now(UTC).replace(tzinfo=None)
    if match is None:
        match = UserPolicyMatch(user_id=user_id, policy_id=policy_id)
        db.add(match)

    match.eligibility_status = eligibility_status
    match.match_score = match_score
    match.satisfied_condition_count = satisfied_condition_count
    match.review_condition_count = review_condition_count
    match.failed_condition_count = failed_condition_count
    match.total_condition_count = total_condition_count
    match.estimated_benefit_amount = estimated_benefit_amount
    match.engine_version = engine_version
    match.evaluated_at = now
    db.flush()

    existing_statement = select(UserPolicyConditionResult).where(
        UserPolicyConditionResult.match_id == match.id
    )
    existing = {result.condition_id: result for result in db.scalars(existing_statement).all()}
    incoming_ids: set[int] = set()
    for payload in condition_results:
        condition_id_raw = payload.get("condition_id")
        if not isinstance(condition_id_raw, int):
            raise ValueError("condition_id is required for every match result")
        incoming_ids.add(condition_id_raw)
        result = existing.get(condition_id_raw)
        if result is None:
            result = UserPolicyConditionResult(
                match_id=match.id,
                condition_id=condition_id_raw,
            )
            db.add(result)
        result.result_status = str(payload["result_status"])
        result.actual_value_json = payload.get("actual_value_json")
        result.reason = str(payload.get("reason") or "")
        result.evaluated_at = now

    for condition_id, stale in existing.items():
        if condition_id not in incoming_ids:
            db.delete(stale)

    db.commit()
    db.refresh(match)
    return match


def get_user_policy_state(
    db: Session,
    *,
    user_id: int,
    policy_id: int,
) -> UserPolicyState | None:
    """Return one user's state for a policy."""

    statement = select(UserPolicyState).where(
        UserPolicyState.user_id == user_id,
        UserPolicyState.policy_id == policy_id,
    )
    return db.scalar(statement)


def get_user_policy_state_by_id(
    db: Session,
    *,
    state_id: int,
    user_id: int,
) -> UserPolicyState | None:
    """Return a state only when it belongs to the requesting user."""

    statement = select(UserPolicyState).where(
        UserPolicyState.id == state_id,
        UserPolicyState.user_id == user_id,
    )
    return db.scalar(statement)


def _get_or_create_state(
    db: Session,
    *,
    user_id: int,
    policy_id: int,
) -> UserPolicyState:
    state = get_user_policy_state(db, user_id=user_id, policy_id=policy_id)
    if state is None:
        state = UserPolicyState(
            user_id=user_id,
            policy_id=policy_id,
            is_bookmarked=False,
            preparation_status="NOT_STARTED",
            progress_percent=0,
            application_status="NOT_APPLIED",
        )
        db.add(state)
        db.flush()
    return state


def set_bookmark(
    db: Session,
    *,
    user_id: int,
    policy_id: int,
    bookmarked: bool,
) -> UserPolicyState:
    """Add or remove a policy from the user's interest list."""

    state = _get_or_create_state(db, user_id=user_id, policy_id=policy_id)
    now = datetime.now(UTC).replace(tzinfo=None)
    state.is_bookmarked = bookmarked
    state.bookmarked_at = now if bookmarked else None
    state.updated_at = now
    db.commit()
    db.refresh(state)
    return state


def start_preparation(
    db: Session,
    *,
    user_id: int,
    policy_id: int,
) -> UserPolicyState:
    """Start a persistent checklist and initialize document rows."""

    state = _get_or_create_state(db, user_id=user_id, policy_id=policy_id)
    now = datetime.now(UTC).replace(tzinfo=None)
    if _enum_code(state.preparation_status) == "NOT_STARTED":
        state.preparation_status = "IN_PROGRESS"
        state.preparation_started_at = now

    document_ids = list(
        db.scalars(select(PolicyDocument.id).where(PolicyDocument.policy_id == policy_id)).all()
    )
    existing_ids = set(
        db.scalars(
            select(UserDocumentProgress.document_id).where(
                UserDocumentProgress.user_policy_state_id == state.id
            )
        ).all()
    )
    for document_id in document_ids:
        if document_id not in existing_ids:
            db.add(
                UserDocumentProgress(
                    user_policy_state_id=state.id,
                    document_id=document_id,
                    preparation_status="NOT_STARTED",
                    is_checked=False,
                    updated_at=now,
                )
            )

    db.flush()
    _recalculate_progress(db, state)
    db.commit()
    db.refresh(state)
    return state


def list_document_progress(
    db: Session,
    state_id: int,
) -> list[UserDocumentProgress]:
    """Return the persisted document checklist rows."""

    statement = (
        select(UserDocumentProgress)
        .where(UserDocumentProgress.user_policy_state_id == state_id)
        .order_by(UserDocumentProgress.document_id.asc())
    )
    return list(db.scalars(statement).all())


def update_document_progress(
    db: Session,
    *,
    user_id: int,
    state_id: int,
    document_id: int,
    preparation_status: str,
    is_checked: bool,
    note: str | None,
) -> UserDocumentProgress:
    """Update one checklist document and refresh the cached percentage."""

    state = get_user_policy_state_by_id(db, state_id=state_id, user_id=user_id)
    if state is None:
        raise LookupError("Preparation state not found")
    statement = select(UserDocumentProgress).where(
        UserDocumentProgress.user_policy_state_id == state_id,
        UserDocumentProgress.document_id == document_id,
    )
    progress = db.scalar(statement)
    if progress is None:
        raise LookupError("Document is not part of this preparation")

    now = datetime.now(UTC).replace(tzinfo=None)
    progress.preparation_status = preparation_status
    progress.is_checked = is_checked
    progress.checked_at = now if is_checked else None
    progress.note = note
    progress.updated_at = now
    db.flush()
    _recalculate_progress(db, state)
    db.commit()
    db.refresh(progress)
    return progress


def confirm_condition(
    db: Session,
    *,
    user_id: int,
    state_id: int,
    condition_id: int,
    confirmed: bool,
) -> UserPolicyConditionResult:
    """Store a user's manual confirmation for a review-required condition."""

    state = get_user_policy_state_by_id(db, state_id=state_id, user_id=user_id)
    if state is None:
        raise LookupError("Preparation state not found")
    match = get_policy_match(db, user_id=user_id, policy_id=state.policy_id)
    if match is None:
        raise LookupError("Policy match must be evaluated before confirmation")

    statement = select(UserPolicyConditionResult).where(
        UserPolicyConditionResult.match_id == match.id,
        UserPolicyConditionResult.condition_id == condition_id,
    )
    result = db.scalar(statement)
    if result is None:
        raise LookupError("Condition result not found")

    now = datetime.now(UTC).replace(tzinfo=None)
    result.is_user_confirmed = confirmed
    result.confirmed_at = now if confirmed else None
    db.flush()
    _recalculate_progress(db, state)
    db.commit()
    db.refresh(result)
    return result


def complete_application(
    db: Session,
    *,
    user_id: int,
    policy_id: int,
    application_date: date,
    application_status: str = "SUBMITTED",
    application_note: str | None = None,
) -> UserPolicyState:
    """Record that a user submitted an application."""

    state = _get_or_create_state(db, user_id=user_id, policy_id=policy_id)
    state.application_status = application_status
    state.application_date = application_date
    state.application_note = application_note
    state.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(state)
    return state


def list_user_policy_states(
    db: Session,
    *,
    user_id: int,
    tab: str | None = None,
    sort: str = "latest",
) -> list[UserPolicyState]:
    """Return interest, preparation, or application states for My Page."""

    statement = select(UserPolicyState).where(UserPolicyState.user_id == user_id)
    if tab == "bookmarked":
        statement = statement.where(UserPolicyState.is_bookmarked.is_(True))
    elif tab == "preparing":
        # 체크리스트가 100% 채워지면 preparation_status가 COMPLETED로 바뀌지만,
        # "신청 완료" 버튼(프론트 미구현)을 실제로 누르기 전까지는 준비 중 탭에
        # 계속 남아있어야 한다. NOT_STARTED만 제외.
        statement = statement.where(
            UserPolicyState.preparation_status != "NOT_STARTED",
            UserPolicyState.application_status == "NOT_APPLIED",
        )
    elif tab == "applied":
        statement = statement.where(UserPolicyState.application_status != "NOT_APPLIED")

    if sort == "deadline":
        statement = statement.join(Policy, Policy.id == UserPolicyState.policy_id)
        statement = statement.order_by(
            Policy.application_end_date.is_(None),
            Policy.application_end_date.asc(),
        )
    else:
        statement = statement.order_by(UserPolicyState.updated_at.desc())
    return list(db.scalars(statement).all())


def list_upcoming_deadline_states(
    db: Session,
    *,
    user_id: int,
    within_days: int,
) -> list[UserPolicyState]:
    """Return bookmarked/in-progress states with a near-term deadline, soonest first."""

    today = date.today()
    cutoff = today + timedelta(days=within_days)
    statement = (
        select(UserPolicyState)
        .join(Policy, Policy.id == UserPolicyState.policy_id)
        .where(UserPolicyState.user_id == user_id)
        .where(
            or_(
                UserPolicyState.is_bookmarked.is_(True),
                (UserPolicyState.preparation_status != "NOT_STARTED")
                & (UserPolicyState.application_status == "NOT_APPLIED"),
            )
        )
        .where(Policy.is_active.is_(True))
        .where(Policy.is_ongoing.is_(False))
        .where(Policy.application_end_date.is_not(None))
        .where(Policy.application_end_date >= today)
        .where(Policy.application_end_date <= cutoff)
        .order_by(Policy.application_end_date.asc())
    )
    return list(db.scalars(statement).all())


def list_cached_matches(db: Session, user_id: int) -> list[UserPolicyMatch]:
    """Return cached recommendations for a user."""

    statement = (
        select(UserPolicyMatch)
        .where(UserPolicyMatch.user_id == user_id)
        .order_by(
            UserPolicyMatch.match_score.desc(),
            UserPolicyMatch.evaluated_at.desc(),
        )
    )
    return list(db.scalars(statement).all())


def _recalculate_progress(db: Session, state: UserPolicyState) -> None:
    """Recompute condition + document completion percentage."""

    match = get_policy_match(db, user_id=state.user_id, policy_id=state.policy_id)
    total_conditions = 0
    completed_conditions = 0
    if match is not None:
        total_conditions = int(
            db.scalar(
                select(func.count(UserPolicyConditionResult.id)).where(
                    UserPolicyConditionResult.match_id == match.id
                )
            )
            or 0
        )
        completed_conditions = int(
            db.scalar(
                select(func.count(UserPolicyConditionResult.id)).where(
                    UserPolicyConditionResult.match_id == match.id,
                    (UserPolicyConditionResult.result_status == "SATISFIED")
                    | UserPolicyConditionResult.is_user_confirmed.is_(True),
                )
            )
            or 0
        )

    total_documents = int(
        db.scalar(
            select(func.count(UserDocumentProgress.id)).where(
                UserDocumentProgress.user_policy_state_id == state.id
            )
        )
        or 0
    )
    completed_documents = int(
        db.scalar(
            select(func.count(UserDocumentProgress.id)).where(
                UserDocumentProgress.user_policy_state_id == state.id,
                UserDocumentProgress.is_checked.is_(True),
            )
        )
        or 0
    )

    total = total_conditions + total_documents
    completed = completed_conditions + completed_documents
    state.progress_percent = round((completed / total) * 100) if total else 0
    now = datetime.now(UTC).replace(tzinfo=None)
    if total > 0 and completed == total:
        state.preparation_status = "COMPLETED"
        state.preparation_completed_at = now
    elif _enum_code(state.preparation_status) != "NOT_STARTED":
        state.preparation_status = "IN_PROGRESS"
        state.preparation_completed_at = None
    state.updated_at = now


def _enum_code(value: object) -> str:
    return str(getattr(value, "value", value))
