"""Policy recommendation orchestration.

The service composes CRUD calls and the pure Policy Engine.  ORM queries remain
confined to ``app.crud`` as required by the project architecture.
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.crud import categories as category_crud
from app.crud import policies as policy_crud
from app.crud import user_policies as state_crud
from app.crud import users as user_crud
from app.models.policy import CalcType, Policy, PolicyBenefit
from app.models.user_policy import EligibilityStatus, UserPolicyMatch
from app.schemas.dashboard import DashboardSummaryResponse, DashboardUpcomingPolicy
from app.services.errors import NotFoundError
from app.services.policy_engine.calc_type import can_simulate, resolve_calc_type
from app.services.policy_engine.matcher import PolicyEvaluation, evaluate_policy

ENGINE_VERSION = "joop-policy-engine-1"


@dataclass(slots=True)
class EvaluatedPolicy:
    """A policy card plus the user's current matching evidence."""

    bundle: policy_crud.PolicyBundle
    evaluation: PolicyEvaluation
    match: UserPolicyMatch
    estimated_benefit_amount: Decimal
    is_simulatable: bool


@dataclass(slots=True)
class EvaluatedPolicyPage:
    """Paginated evaluated policies."""

    items: list[EvaluatedPolicy]
    total: int
    page: int
    size: int


def build_user_context(db: Session, user_id: int) -> dict[str, object]:
    """Build the fixed condition-key registry from persisted profile answers."""

    profile = user_crud.get_user_profile(db, user_id)
    profile_values: dict[str, object] = {}
    if profile is not None:
        fields = (
            "birth_year",
            "region_code",
            "region_sido",
            "region_sigungu",
            "income_band_code",
            "employment_status_code",
            "household_type_code",
            "household_size",
            "housing_type_code",
        )
        profile_values = {field: getattr(profile, field, None) for field in fields}
        birth_year = profile_values.get("birth_year")
        if isinstance(birth_year, int):
            profile_values["age"] = date.today().year - birth_year

    context: dict[str, object] = {"profile": profile_values}
    for dotted_key, value in category_crud.get_user_answer_values(db, user_id).items():
        _set_nested_value(context, dotted_key, value)
    return context


def evaluate_policy_for_user(
    db: Session,
    *,
    user_id: int,
    policy_id: int,
    context: Mapping[str, object] | None = None,
) -> EvaluatedPolicy:
    """Evaluate and cache one policy for one user."""

    bundle = policy_crud.get_policy_bundle(db, policy_id)
    if bundle is None or not bundle.policy.is_active:
        raise NotFoundError("정책을 찾을 수 없습니다.")
    user_context = dict(context) if context is not None else build_user_context(db, user_id)
    evaluation = evaluate_policy(bundle.conditions, user_context)
    if _is_application_closed(bundle.policy):
        evaluation = replace(evaluation, status=EligibilityStatus.INELIGIBLE)
    estimated_benefit = _estimate_max_benefit(bundle.benefits)
    total = evaluation.total_condition_count
    score = (
        (Decimal(evaluation.satisfied_condition_count) / Decimal(total)) * Decimal(100)
        if total
        else Decimal(100)
    ).quantize(Decimal("0.01"))

    condition_payloads: list[dict[str, object]] = []
    for condition, result in zip(
        bundle.conditions,
        evaluation.condition_results,
        strict=True,
    ):
        condition_payloads.append(
            {
                "condition_id": condition.id,
                "result_status": _condition_db_status(result.status),
                "actual_value_json": {"value": _json_safe(result.actual_value)},
                "reason": result.reason,
            }
        )

    match = state_crud.upsert_policy_match(
        db,
        user_id=user_id,
        policy_id=policy_id,
        eligibility_status=evaluation.status.value,
        match_score=score,
        satisfied_condition_count=evaluation.satisfied_condition_count,
        review_condition_count=evaluation.review_condition_count,
        failed_condition_count=evaluation.unsatisfied_condition_count,
        total_condition_count=total,
        estimated_benefit_amount=estimated_benefit,
        engine_version=ENGINE_VERSION,
        condition_results=condition_payloads,
    )
    return EvaluatedPolicy(
        bundle=bundle,
        evaluation=evaluation,
        match=match,
        estimated_benefit_amount=estimated_benefit,
        is_simulatable=_is_policy_simulatable(bundle),
    )


def list_evaluated_policies(
    db: Session,
    *,
    user_id: int,
    category_code: str | None,
    eligibility_status: str | None,
    sort: str,
    keyword: str | None,
    page: int,
    size: int,
) -> EvaluatedPolicyPage:
    """Evaluate a policy collection and apply user-facing list ordering."""

    fetch_size = 500 if sort == "recommendation" or eligibility_status else size
    fetch_page = 1 if fetch_size == 500 else page
    policies, database_total = policy_crud.list_policies(
        db,
        category_code=category_code,
        keyword=keyword,
        page=fetch_page,
        size=fetch_size,
        sort=sort,
    )
    context = build_user_context(db, user_id)
    evaluated = [
        evaluate_policy_for_user(
            db,
            user_id=user_id,
            policy_id=policy.id,
            context=context,
        )
        for policy in policies
    ]
    if eligibility_status:
        normalized = eligibility_status.upper()
        evaluated = [
            item
            for item in evaluated
            if str(item.match.eligibility_status).split(".")[-1] == normalized
        ]
    if sort == "recommendation":
        evaluated.sort(key=_recommendation_sort_key, reverse=True)

    if fetch_size == 500:
        total = len(evaluated)
        start = (page - 1) * size
        evaluated = evaluated[start : start + size]
    else:
        total = database_total
    return EvaluatedPolicyPage(items=evaluated, total=total, page=page, size=size)


def list_recommendations(
    db: Session,
    *,
    user_id: int,
    limit: int | None = None,
    eligibility_status: str | None = None,
) -> list[EvaluatedPolicy]:
    """Return category-independent recommendations in match order."""

    page = list_evaluated_policies(
        db,
        user_id=user_id,
        category_code=None,
        eligibility_status=eligibility_status,
        sort="recommendation",
        keyword=None,
        page=1,
        size=limit or 100,
    )
    return page.items[:limit] if limit is not None else page.items


def get_dashboard_summary(
    db: Session,
    *,
    user_id: int,
    upcoming_within_days: int = 30,
) -> DashboardSummaryResponse:
    """Aggregate the home dashboard: nearest deadline and missed ELIGIBLE benefits."""

    states = state_crud.list_upcoming_deadline_states(
        db,
        user_id=user_id,
        within_days=upcoming_within_days,
    )
    nearest = None
    if states:
        top_policy = states[0].policy
        nearest = DashboardUpcomingPolicy(
            policy_id=top_policy.id,
            title=top_policy.title,
            summary=top_policy.summary,
            application_end_date=top_policy.application_end_date,
            days_until_deadline=(top_policy.application_end_date - date.today()).days,
        )

    eligible_page = list_evaluated_policies(
        db,
        user_id=user_id,
        category_code=None,
        eligibility_status="ELIGIBLE",
        sort="latest",
        keyword=None,
        page=1,
        size=500,
    )
    total_amount = sum(
        (item.estimated_benefit_amount for item in eligible_page.items),
        Decimal("0"),
    )

    return DashboardSummaryResponse(
        upcoming_deadline_policy=nearest,
        upcoming_deadline_count=len(states),
        missed_benefit_total_amount=total_amount,
        missed_benefit_policy_count=len(eligible_page.items),
    )


def get_policy_entity(db: Session, policy_id: int) -> Policy:
    """Return a policy or a domain-level not-found error."""

    policy = policy_crud.get_policy(db, policy_id)
    if policy is None:
        raise NotFoundError("정책을 찾을 수 없습니다.")
    return policy


def _is_application_closed(policy: Policy) -> bool:
    """A policy whose application window has passed is never ELIGIBLE/NEEDS_REVIEW,
    regardless of how well the user's profile matches its conditions."""

    if policy.is_ongoing:
        return False
    return policy.application_end_date is not None and policy.application_end_date < date.today()


def _estimate_max_benefit(benefits: list[object]) -> Decimal:
    total = Decimal(0)
    for benefit in benefits:
        max_total = getattr(benefit, "max_total_amount", None)
        if max_total is not None:
            total += Decimal(max_total)
            continue
        maximum = getattr(benefit, "max_amount", None)
        if maximum is None:
            continue
        months = getattr(benefit, "duration_months", None) or 1
        cycle = str(getattr(benefit, "payment_cycle", "")).split(".")[-1]
        multiplier = int(months) if cycle == "MONTHLY" else 1
        total += Decimal(maximum) * multiplier
    return total


def build_policy_like_for_calc_type(bundle: policy_crud.PolicyBundle) -> object:
    """Build the minimal category_links shape resolve_calc_type()/can_simulate()
    need (see policy_engine.calc_type), reusing bundle.categories - already
    loaded - instead of touching bundle.policy.category_links, which would
    trigger an extra lazy-load query per policy."""

    return SimpleNamespace(
        category_links=[SimpleNamespace(category=category) for category in bundle.categories]
    )


def resolve_bundle_benefit_calc_type(
    bundle: policy_crud.PolicyBundle,
    benefit: PolicyBenefit,
) -> CalcType | None:
    """Public wrapper so routes can expose PolicyBenefitResponse.calc_type."""

    return resolve_calc_type(benefit, build_policy_like_for_calc_type(bundle))


def _is_policy_simulatable(bundle: policy_crud.PolicyBundle) -> bool:
    """True if the simulator can run at least one benefit on this policy."""

    policy_like = build_policy_like_for_calc_type(bundle)
    return any(can_simulate(benefit, policy_like) for benefit in bundle.benefits)


def _set_nested_value(target: dict[str, object], dotted_key: str, value: object) -> None:
    parts = dotted_key.split(".")
    cursor = target
    for part in parts[:-1]:
        child = cursor.get(part)
        if not isinstance(child, dict):
            child = {}
            cursor[part] = child
        cursor = child
    cursor[parts[-1]] = value


def _condition_db_status(status: object) -> str:
    name = str(getattr(status, "name", status)).split(".")[-1]
    return {
        "SATISFIED": "SATISFIED",
        "NEEDS_REVIEW": "NEEDS_REVIEW",
        "UNSATISFIED": "UNSATISFIED",
    }.get(name, "NEEDS_REVIEW")


_STATUS_SORT_PRIORITY: Mapping[EligibilityStatus, int] = {
    EligibilityStatus.ELIGIBLE: 2,
    EligibilityStatus.NEEDS_REVIEW: 1,
    EligibilityStatus.INELIGIBLE: 0,
}


def _status_sort_priority(item: EvaluatedPolicy) -> int:
    """추천순: 가능성 높음 → 추가 확인 필요 → 불충족 3단계로 정렬한다(user_flow 7절)."""

    return _STATUS_SORT_PRIORITY.get(item.evaluation.status, 0)


def _recommendation_sort_key(item: EvaluatedPolicy) -> tuple[int, Decimal, date]:
    """정렬 키: 상태 우선순위 → match_score → 공고일, 모두 내림차순으로 정렬한다.

    match_score만으로 정렬하면 필수 조건이 하나 불충족돼 INELIGIBLE인 정책이
    다른 조건을 많이 만족해 점수가 높다는 이유로 NEEDS_REVIEW 정책보다 앞설 수
    있다(gpt의견 4-4절). 상태 우선순위를 1순위 정렬 기준으로 둬 이를 막는다.
    """

    return (
        _status_sort_priority(item),
        item.match.match_score,
        item.bundle.policy.published_date or date.min,
    )


def _json_safe(value: object) -> object:
    if isinstance(value, (date, Decimal)):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value
