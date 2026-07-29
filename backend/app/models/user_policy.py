"""Cached policy evaluations and each user's policy workflow state."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import (
    BIGINT_UNSIGNED,
    DATETIME_FSP6,
    TimestampMixin,
    varchar_enum,
)

if TYPE_CHECKING:
    from app.models.policy import Policy
    from app.models.policy_condition import PolicyCondition
    from app.models.user import User
    from app.models.user_document_progress import UserDocumentProgress


class EligibilityStatus(str, Enum):
    """Internal three-state cached policy evaluation."""

    ELIGIBLE = "ELIGIBLE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    INELIGIBLE = "INELIGIBLE"


class ConditionResultStatus(str, Enum):
    """Stored result for one policy condition."""

    SATISFIED = "SATISFIED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    UNSATISFIED = "UNSATISFIED"


class PreparationStatus(str, Enum):
    """Overall checklist preparation state."""

    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class ApplicationStatus(str, Enum):
    """User-reported application lifecycle."""

    NOT_APPLIED = "NOT_APPLIED"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAID = "PAID"


class UserPolicyMatch(Base):
    """Cached result of evaluating one policy for one user."""

    __tablename__ = "user_policy_matches"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "policy_id",
            name="uk_user_policy_match",
        ),
        CheckConstraint(
            "match_score >= 0 AND match_score <= 100",
            name="match_score_range",
        ),
        CheckConstraint(
            "satisfied_condition_count >= 0",
            name="satisfied_count_nonnegative",
        ),
        CheckConstraint(
            "review_condition_count >= 0",
            name="review_count_nonnegative",
        ),
        CheckConstraint(
            "failed_condition_count >= 0",
            name="failed_count_nonnegative",
        ),
        CheckConstraint(
            "total_condition_count >= 0",
            name="total_count_nonnegative",
        ),
        CheckConstraint(
            "estimated_benefit_amount IS NULL OR estimated_benefit_amount >= 0",
            name="estimated_benefit_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    eligibility_status: Mapped[EligibilityStatus] = mapped_column(
        varchar_enum(
            EligibilityStatus,
            name="eligibility_status_enum",
            length=30,
        ),
        nullable=False,
    )
    match_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0,
        server_default="0",
    )
    satisfied_condition_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    review_condition_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    failed_condition_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_condition_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    estimated_benefit_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    engine_version: Mapped[str] = mapped_column(String(30), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DATETIME_FSP6,
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    user: Mapped[User] = relationship(back_populates="policy_matches")
    policy: Mapped[Policy] = relationship(back_populates="user_matches")
    condition_results: Mapped[list[UserPolicyConditionResult]] = relationship(
        back_populates="match",
        cascade="all, delete-orphan",
    )


class UserPolicyConditionResult(Base):
    """Cached per-condition evidence displayed on policy detail pages."""

    __tablename__ = "user_policy_condition_results"
    __table_args__ = (
        UniqueConstraint(
            "match_id",
            "condition_id",
            name="uk_match_condition",
        ),
    )

    id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        primary_key=True,
        autoincrement=True,
    )
    match_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("user_policy_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    condition_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("policy_conditions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    result_status: Mapped[ConditionResultStatus] = mapped_column(
        varchar_enum(
            ConditionResultStatus,
            name="condition_result_status_enum",
            length=30,
        ),
        nullable=False,
    )
    actual_value_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_user_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DATETIME_FSP6,
        nullable=True,
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DATETIME_FSP6,
        nullable=False,
        server_default=func.now(),
    )

    match: Mapped[UserPolicyMatch] = relationship(back_populates="condition_results")
    condition: Mapped[PolicyCondition] = relationship(back_populates="evaluation_results")


class UserPolicyState(TimestampMixin, Base):
    """Bookmark, preparation, and application state for a user-policy pair."""

    __tablename__ = "user_policy_states"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "policy_id",
            name="uk_user_policy_state",
        ),
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="progress_percent_range",
        ),
    )

    id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_bookmarked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    bookmarked_at: Mapped[datetime | None] = mapped_column(
        DATETIME_FSP6,
        nullable=True,
    )
    preparation_status: Mapped[PreparationStatus] = mapped_column(
        varchar_enum(
            PreparationStatus,
            name="preparation_status_enum",
            length=30,
        ),
        nullable=False,
        default=PreparationStatus.NOT_STARTED,
        server_default=PreparationStatus.NOT_STARTED.value,
    )
    preparation_started_at: Mapped[datetime | None] = mapped_column(
        DATETIME_FSP6,
        nullable=True,
    )
    preparation_completed_at: Mapped[datetime | None] = mapped_column(
        DATETIME_FSP6,
        nullable=True,
    )
    progress_percent: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    application_status: Mapped[ApplicationStatus] = mapped_column(
        varchar_enum(
            ApplicationStatus,
            name="application_status_enum",
            length=30,
        ),
        nullable=False,
        default=ApplicationStatus.NOT_APPLIED,
        server_default=ApplicationStatus.NOT_APPLIED.value,
    )
    application_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    application_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user: Mapped[User] = relationship(back_populates="policy_states")
    policy: Mapped[Policy] = relationship(back_populates="user_states")
    document_progress: Mapped[list[UserDocumentProgress]] = relationship(
        back_populates="user_policy_state",
        cascade="all, delete-orphan",
    )


__all__ = [
    "ApplicationStatus",
    "ConditionResultStatus",
    "EligibilityStatus",
    "PreparationStatus",
    "UserPolicyConditionResult",
    "UserPolicyMatch",
    "UserPolicyState",
]
