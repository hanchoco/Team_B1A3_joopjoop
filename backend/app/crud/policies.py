"""Policy, benefit, condition, and document database access."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.models.policy import Policy, PolicyBenefit, PolicyCategory
from app.models.policy_condition import PolicyCondition
from app.models.policy_document import PolicyDocument
from app.models.user_category_profile import Category


@dataclass(slots=True)
class PolicyBundle:
    """Policy data required by detail, matching, and checklist services."""

    policy: Policy
    categories: list[Category]
    benefits: list[PolicyBenefit]
    conditions: list[PolicyCondition]
    documents: list[PolicyDocument]


def get_policy(db: Session, policy_id: int) -> Policy | None:
    """Return one active or inactive policy by primary key."""

    return db.get(Policy, policy_id)


def list_policy_categories(db: Session, policy_id: int) -> list[Category]:
    """Return all categories attached to a policy, primary first."""

    statement = (
        select(Category)
        .join(PolicyCategory, PolicyCategory.category_id == Category.id)
        .where(PolicyCategory.policy_id == policy_id)
        .order_by(PolicyCategory.is_primary.desc(), Category.display_order.asc())
    )
    return list(db.scalars(statement).all())


def list_policy_benefits(db: Session, policy_id: int) -> list[PolicyBenefit]:
    """Return benefit calculation definitions for a policy."""

    statement = (
        select(PolicyBenefit)
        .where(PolicyBenefit.policy_id == policy_id)
        .order_by(PolicyBenefit.id.asc())
    )
    return list(db.scalars(statement).all())


def list_policy_conditions(db: Session, policy_id: int) -> list[PolicyCondition]:
    """Return policy conditions in their detail-page order."""

    statement = (
        select(PolicyCondition)
        .where(PolicyCondition.policy_id == policy_id)
        .order_by(
            PolicyCondition.condition_group_no.asc(),
            PolicyCondition.sort_order.asc(),
            PolicyCondition.id.asc(),
        )
    )
    return list(db.scalars(statement).all())


def list_policy_documents(db: Session, policy_id: int) -> list[PolicyDocument]:
    """Return application documents in checklist order."""

    statement = (
        select(PolicyDocument)
        .where(PolicyDocument.policy_id == policy_id)
        .order_by(PolicyDocument.display_order.asc(), PolicyDocument.id.asc())
    )
    return list(db.scalars(statement).all())


def get_policy_bundle(db: Session, policy_id: int) -> PolicyBundle | None:
    """Return a policy and all read models used by its detail page."""

    policy = get_policy(db, policy_id)
    if policy is None:
        return None
    return PolicyBundle(
        policy=policy,
        categories=list_policy_categories(db, policy_id),
        benefits=list_policy_benefits(db, policy_id),
        conditions=list_policy_conditions(db, policy_id),
        documents=list_policy_documents(db, policy_id),
    )


def list_policies(
    db: Session,
    *,
    category_code: str | None = None,
    keyword: str | None = None,
    active_only: bool = True,
    page: int = 1,
    size: int = 20,
    sort: str = "latest",
) -> tuple[list[Policy], int]:
    """Return a filtered, paginated policy collection and total count."""

    statement = select(Policy)
    count_statement = select(func.count(func.distinct(Policy.id)))

    if category_code is not None:
        joins = (
            (PolicyCategory, PolicyCategory.policy_id == Policy.id),
            (Category, Category.id == PolicyCategory.category_id),
        )
        for target, condition in joins:
            statement = statement.join(target, condition)
            count_statement = count_statement.join(target, condition)
        category_filter = Category.code == category_code.upper()
        statement = statement.where(category_filter)
        count_statement = count_statement.where(category_filter)

    if active_only:
        active_filter = Policy.is_active.is_(True)
        statement = statement.where(active_filter)
        count_statement = count_statement.where(active_filter)

    if keyword:
        normalized = f"%{keyword.strip()}%"
        keyword_filter = or_(
            Policy.title.ilike(normalized),
            Policy.summary.ilike(normalized),
            Policy.description.ilike(normalized),
        )
        statement = statement.where(keyword_filter)
        count_statement = count_statement.where(keyword_filter)

    if sort == "deadline":
        statement = statement.order_by(
            Policy.application_end_date.is_(None),
            Policy.application_end_date.asc(),
            Policy.id.desc(),
        )
    else:
        statement = statement.order_by(
            Policy.published_date.desc(),
            Policy.created_at.desc(),
            Policy.id.desc(),
        )

    total = int(db.scalar(count_statement) or 0)
    statement = statement.distinct().offset((page - 1) * size).limit(size)
    return list(db.scalars(statement).all()), total


def list_policies_by_ids(db: Session, policy_ids: Sequence[int]) -> list[Policy]:
    """Return policies while preserving the input ordering."""

    if not policy_ids:
        return []
    statement = select(Policy).where(Policy.id.in_(policy_ids))
    records = {policy.id: policy for policy in db.scalars(statement).all()}
    return [records[policy_id] for policy_id in policy_ids if policy_id in records]


def upsert_policy_bundle(
    db: Session,
    normalized_policy: Mapping[str, object],
) -> Policy:
    """Persist a human-approved normalized policy bundle.

    The AI modules only create review drafts.  The seed command is responsible
    for calling this function after the operator explicitly supplies
    ``--approve``.
    """

    source = normalized_policy.get("source")
    external_id = normalized_policy.get("external_id")
    if not isinstance(source, str) or not isinstance(external_id, str):
        raise ValueError("Approved policy requires source and external_id")

    statement = select(Policy).where(
        Policy.source == source,
        Policy.external_id == external_id,
    )
    policy = db.scalar(statement)
    policy_payload = normalized_policy.get("policy", normalized_policy)
    if not isinstance(policy_payload, Mapping):
        raise ValueError("policy must be an object")

    writable_policy_fields = {
        "source",
        "external_id",
        "title",
        "summary",
        "description",
        "support_target_text",
        "support_content_text",
        "application_method",
        "provider_name",
        "application_url",
        "application_start_date",
        "application_end_date",
        "is_ongoing",
        "published_date",
        "status",
        "raw_payload",
        "source_updated_at",
        "subcategory",
        "region_scope",
        "region_code",
        "contact",
        "original_text",
        "is_active",
    }
    values = {
        field: policy_payload[field] for field in writable_policy_fields if field in policy_payload
    }
    values.setdefault("source", source)
    values.setdefault("external_id", external_id)

    if policy is None:
        policy = Policy(**values)
        db.add(policy)
        db.flush()
    else:
        for field, value in values.items():
            setattr(policy, field, value)
        policy.updated_at = datetime.now(UTC).replace(tzinfo=None)
        db.flush()

    categories_payload = normalized_policy.get("category_codes")
    if isinstance(categories_payload, Sequence) and not isinstance(
        categories_payload, (str, bytes)
    ):
        db.execute(delete(PolicyCategory).where(PolicyCategory.policy_id == policy.id))
        for position, category_code in enumerate(categories_payload):
            if not isinstance(category_code, str):
                continue
            category = db.scalar(select(Category).where(Category.code == category_code.upper()))
            if category is not None:
                db.add(
                    PolicyCategory(
                        policy_id=policy.id,
                        category_id=category.id,
                        is_primary=position == 0,
                    )
                )

    _replace_policy_children(
        db,
        policy_id=policy.id,
        payload=normalized_policy,
        key="benefits",
        model=PolicyBenefit,
    )
    _replace_policy_children(
        db,
        policy_id=policy.id,
        payload=normalized_policy,
        key="conditions",
        model=PolicyCondition,
    )
    _replace_policy_children(
        db,
        policy_id=policy.id,
        payload=normalized_policy,
        key="documents",
        model=PolicyDocument,
    )

    db.commit()
    db.refresh(policy)
    return policy


def _replace_policy_children(
    db: Session,
    *,
    policy_id: int,
    payload: Mapping[str, object],
    key: str,
    model: type[PolicyBenefit] | type[PolicyCondition] | type[PolicyDocument],
) -> None:
    """Replace one approved child collection when present in a seed bundle."""

    raw_items = payload.get(key)
    if raw_items is None:
        return
    if not isinstance(raw_items, Sequence) or isinstance(raw_items, (str, bytes)):
        raise ValueError(f"{key} must be an array")

    db.execute(delete(model).where(cast(object, model.policy_id) == policy_id))
    for item in raw_items:
        if not isinstance(item, Mapping):
            raise ValueError(f"Every {key} item must be an object")
        values = dict(item)
        values.pop("id", None)
        values["policy_id"] = policy_id
        db.add(model(**values))
