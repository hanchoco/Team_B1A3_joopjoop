"""Policy source data, category links, and benefit definitions."""

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
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import (
    BIGINT_UNSIGNED,
    DATETIME_FSP6,
    LONGTEXT_TYPE,
    SMALLINT_UNSIGNED,
    TimestampMixin,
    varchar_enum,
)

if TYPE_CHECKING:
    from app.models.notification_setting import Notification
    from app.models.policy_condition import PolicyCondition
    from app.models.policy_document import PolicyDocument
    from app.models.user_category_profile import Category
    from app.models.user_policy import UserPolicyMatch, UserPolicyState


class PolicySource(str, Enum):
    """Origin of a policy record."""

    ONTONG_YOUTH = "ONTONG_YOUTH"
    MANUAL = "MANUAL"


class PolicyStatus(str, Enum):
    """Publication lifecycle of policy source data."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class BenefitType(str, Enum):
    """Semantic kind of support a policy provides."""

    CASH = "CASH"
    DISCOUNT = "DISCOUNT"
    LOAN = "LOAN"
    SAVINGS = "SAVINGS"
    TAX_REDUCTION = "TAX_REDUCTION"
    SERVICE = "SERVICE"
    OTHER = "OTHER"


class AmountType(str, Enum):
    """How a benefit amount should be calculated."""

    FIXED = "FIXED"
    RANGE = "RANGE"
    FORMULA = "FORMULA"
    VARIABLE = "VARIABLE"


class PaymentCycle(str, Enum):
    """Benefit payment cadence."""

    ONCE = "ONCE"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"
    MATURITY = "MATURITY"
    VARIABLE = "VARIABLE"


class Policy(TimestampMixin, Base):
    """Normalized policy record collected from an integration or entered manually."""

    __tablename__ = "policies"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            name="uk_policy_source_external_id",
        ),
        Index(
            "ix_policies_active_status_deadline",
            "is_active",
            "status",
            "application_end_date",
        ),
        Index("ix_policies_published_date", "published_date"),
    )

    id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        primary_key=True,
        autoincrement=True,
    )
    source: Mapped[PolicySource] = mapped_column(
        varchar_enum(
            PolicySource,
            name="policy_source_enum",
            length=30,
        ),
        nullable=False,
        default=PolicySource.MANUAL,
        server_default=PolicySource.MANUAL.value,
    )
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(LONGTEXT_TYPE, nullable=True)
    support_target_text: Mapped[str | None] = mapped_column(
        LONGTEXT_TYPE,
        nullable=True,
    )
    support_content_text: Mapped[str | None] = mapped_column(
        LONGTEXT_TYPE,
        nullable=True,
    )
    application_method: Mapped[str | None] = mapped_column(
        LONGTEXT_TYPE,
        nullable=True,
    )
    provider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    application_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    application_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    application_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_ongoing: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[PolicyStatus] = mapped_column(
        varchar_enum(
            PolicyStatus,
            name="policy_status_enum",
            length=20,
        ),
        nullable=False,
        default=PolicyStatus.DRAFT,
        server_default=PolicyStatus.DRAFT.value,
    )
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DATETIME_FSP6,
        nullable=True,
    )
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region_scope: Mapped[str | None] = mapped_column(String(20), nullable=True)
    region_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_text: Mapped[str | None] = mapped_column(LONGTEXT_TYPE, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    category_links: Mapped[list[PolicyCategory]] = relationship(
        back_populates="policy",
        cascade="all, delete-orphan",
    )
    benefits: Mapped[list[PolicyBenefit]] = relationship(
        back_populates="policy",
        cascade="all, delete-orphan",
    )
    conditions: Mapped[list[PolicyCondition]] = relationship(
        back_populates="policy",
        cascade="all, delete-orphan",
        order_by="PolicyCondition.sort_order",
    )
    documents: Mapped[list[PolicyDocument]] = relationship(
        back_populates="policy",
        cascade="all, delete-orphan",
        order_by="PolicyDocument.display_order",
    )
    user_matches: Mapped[list[UserPolicyMatch]] = relationship(
        back_populates="policy",
        cascade="all, delete-orphan",
    )
    user_states: Mapped[list[UserPolicyState]] = relationship(
        back_populates="policy",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list[Notification]] = relationship(back_populates="policy")


class PolicyCategory(Base):
    """Many-to-many association between policies and categories."""

    __tablename__ = "policy_categories"

    policy_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("policies.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id: Mapped[int] = mapped_column(
        SMALLINT_UNSIGNED,
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    policy: Mapped[Policy] = relationship(back_populates="category_links")
    category: Mapped[Category] = relationship(back_populates="policy_links")


class PolicyBenefit(TimestampMixin, Base):
    """Structured benefit used by category-specific simulators."""

    __tablename__ = "policy_benefits"
    __table_args__ = (
        CheckConstraint(
            "min_amount IS NULL OR min_amount >= 0",
            name="min_amount_nonnegative",
        ),
        CheckConstraint(
            "max_amount IS NULL OR max_amount >= 0",
            name="max_amount_nonnegative",
        ),
        CheckConstraint(
            "max_total_amount IS NULL OR max_total_amount >= 0",
            name="max_total_amount_nonnegative",
        ),
        CheckConstraint(
            "min_amount IS NULL OR max_amount IS NULL OR min_amount <= max_amount",
            name="amount_range_order",
        ),
        CheckConstraint(
            "duration_months IS NULL OR duration_months > 0",
            name="duration_months_positive",
        ),
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
    benefit_type: Mapped[BenefitType] = mapped_column(
        varchar_enum(
            BenefitType,
            name="benefit_type_enum",
            length=30,
        ),
        nullable=False,
    )
    amount_type: Mapped[AmountType] = mapped_column(
        varchar_enum(
            AmountType,
            name="amount_type_enum",
            length=30,
        ),
        nullable=False,
    )
    min_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    max_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    payment_cycle: Mapped[PaymentCycle | None] = mapped_column(
        varchar_enum(
            PaymentCycle,
            name="payment_cycle_enum",
            length=20,
        ),
        nullable=True,
    )
    duration_months: Mapped[int | None] = mapped_column(
        SMALLINT_UNSIGNED,
        nullable=True,
    )
    max_total_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    calculation_rule_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    display_text: Mapped[str | None] = mapped_column(String(500), nullable=True)

    policy: Mapped[Policy] = relationship(back_populates="benefits")


__all__ = [
    "AmountType",
    "BenefitType",
    "PaymentCycle",
    "Policy",
    "PolicyBenefit",
    "PolicyCategory",
    "PolicySource",
    "PolicyStatus",
]
