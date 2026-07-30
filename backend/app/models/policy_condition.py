"""Confirmed, structured policy eligibility conditions."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    SmallInteger,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BIGINT_UNSIGNED, TimestampMixin, varchar_enum

if TYPE_CHECKING:
    from app.models.policy import Policy
    from app.models.user_policy import UserPolicyConditionResult


class ConditionOperator(str, Enum):
    """Supported operators in the matching rule registry."""

    EQ = "EQ"
    NE = "NE"
    IN = "IN"
    NOT_IN = "NOT_IN"
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    BETWEEN = "BETWEEN"
    CONTAINS_ANY = "CONTAINS_ANY"
    CONTAINS_ALL = "CONTAINS_ALL"
    EXISTS = "EXISTS"
    MANUAL_CHECK = "MANUAL_CHECK"


class CheckMode(str, Enum):
    """How a condition can be verified."""

    AUTO = "AUTO"
    MANUAL = "MANUAL"
    DOCUMENT = "DOCUMENT"


class PolicyCondition(TimestampMixin, Base):
    """One atomic condition evaluated by ``policy_engine.matcher``."""

    __tablename__ = "policy_conditions"
    __table_args__ = (
        CheckConstraint(
            "condition_group_no > 0",
            name="condition_group_no_positive",
        ),
        CheckConstraint("sort_order >= 0", name="sort_order_nonnegative"),
    )

    id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        primary_key=True,
        autoincrement=True,
    )
    policy_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    condition_key: Mapped[str] = mapped_column(String(100), nullable=False)
    operator: Mapped[ConditionOperator] = mapped_column(
        varchar_enum(
            ConditionOperator,
            name="condition_operator_enum",
            length=30,
        ),
        nullable=False,
    )
    expected_value_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    condition_group_no: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
        server_default="1",
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    check_mode: Mapped[CheckMode] = mapped_column(
        varchar_enum(
            CheckMode,
            name="check_mode_enum",
            length=20,
        ),
        nullable=False,
        default=CheckMode.AUTO,
        server_default=CheckMode.AUTO.value,
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    failure_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
    )

    policy: Mapped[Policy] = relationship(back_populates="conditions")
    evaluation_results: Mapped[list[UserPolicyConditionResult]] = relationship(
        back_populates="condition",
        cascade="all, delete-orphan",
    )


__all__ = ["CheckMode", "ConditionOperator", "PolicyCondition"]
