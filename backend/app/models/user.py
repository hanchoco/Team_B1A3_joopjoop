"""User account, matching profile, and consent models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import (
    BIGINT_UNSIGNED,
    DATETIME_FSP6,
    SMALLINT_UNSIGNED,
    TimestampMixin,
    varchar_enum,
)

if TYPE_CHECKING:
    from app.models.notification_setting import Notification, NotificationSetting
    from app.models.user_category_profile import UserCategoryAnswer
    from app.models.user_policy import UserPolicyMatch, UserPolicyState


class AccountStatus(str, Enum):
    """Lifecycle state of a login account."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    WITHDRAWN = "WITHDRAWN"


class EmploymentStatusCode(str, Enum):
    """Normalized employment profile values."""

    EMPLOYED = "EMPLOYED"
    SELF_EMPLOYED = "SELF_EMPLOYED"
    UNEMPLOYED = "UNEMPLOYED"
    JOB_SEEKER = "JOB_SEEKER"
    STUDENT = "STUDENT"
    ON_LEAVE = "ON_LEAVE"
    OTHER = "OTHER"


class HouseholdTypeCode(str, Enum):
    """Normalized household profile values."""

    SINGLE = "SINGLE"
    COUPLE = "COUPLE"
    WITH_PARENTS = "WITH_PARENTS"
    SINGLE_PARENT = "SINGLE_PARENT"
    MULTI_PERSON = "MULTI_PERSON"
    OTHER = "OTHER"


class HousingTypeCode(str, Enum):
    """Normalized housing profile values."""

    OWNED = "OWNED"
    JEONSE = "JEONSE"
    MONTHLY_RENT = "MONTHLY_RENT"
    PUBLIC_RENTAL = "PUBLIC_RENTAL"
    DORMITORY = "DORMITORY"
    WITH_FAMILY = "WITH_FAMILY"
    OTHER = "OTHER"


class IncomeBandCode(str, Enum):
    """Median-income ratio bands used by policy matching."""

    BELOW_50 = "BELOW_50"
    BETWEEN_50_75 = "BETWEEN_50_75"
    BETWEEN_75_100 = "BETWEEN_75_100"
    BETWEEN_100_120 = "BETWEEN_100_120"
    BETWEEN_120_150 = "BETWEEN_120_150"
    ABOVE_150 = "ABOVE_150"
    UNKNOWN = "UNKNOWN"


class ConsentType(str, Enum):
    """Supported terms and privacy consent records."""

    TERMS_REQUIRED = "TERMS_REQUIRED"
    PRIVACY_REQUIRED = "PRIVACY_REQUIRED"
    MARKETING_OPTIONAL = "MARKETING_OPTIONAL"
    THIRD_PARTY_OPTIONAL = "THIRD_PARTY_OPTIONAL"


class User(TimestampMixin, Base):
    """Login identity and account lifecycle."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "length(email) > 3",
            name="email_not_blank",
        ),
    )

    id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        primary_key=True,
        autoincrement=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(50), nullable=True)
    account_status: Mapped[AccountStatus] = mapped_column(
        varchar_enum(
            AccountStatus,
            name="account_status_enum",
            length=20,
        ),
        nullable=False,
        default=AccountStatus.ACTIVE,
        server_default=AccountStatus.ACTIVE.value,
        index=True,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DATETIME_FSP6,
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DATETIME_FSP6,
        nullable=True,
    )

    profile: Mapped[UserProfile | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        single_parent=True,
        uselist=False,
    )
    consents: Mapped[list[UserConsent]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    category_answers: Mapped[list[UserCategoryAnswer]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    policy_matches: Mapped[list[UserPolicyMatch]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    policy_states: Mapped[list[UserPolicyState]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notification_setting: Mapped[NotificationSetting | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        single_parent=True,
        uselist=False,
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserProfile(TimestampMixin, Base):
    """Stable user attributes consumed by the policy matching engine.

    Simulator-only monetary values are intentionally excluded.  They are
    supplied for each simulation request and are never persisted here.
    """

    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint(
            "birth_year IS NULL OR (birth_year BETWEEN 1900 AND 2100)",
            name="birth_year_range",
        ),
        CheckConstraint(
            "household_size IS NULL OR household_size > 0",
            name="household_size_positive",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    birth_year: Mapped[int | None] = mapped_column(
        SMALLINT_UNSIGNED,
        nullable=True,
    )
    region_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    region_sido: Mapped[str | None] = mapped_column(String(30), nullable=True)
    region_sigungu: Mapped[str | None] = mapped_column(String(30), nullable=True)
    income_band_code: Mapped[IncomeBandCode | None] = mapped_column(
        varchar_enum(
            IncomeBandCode,
            name="income_band_code_enum",
            length=30,
        ),
        nullable=True,
    )
    employment_status_code: Mapped[EmploymentStatusCode | None] = mapped_column(
        varchar_enum(
            EmploymentStatusCode,
            name="employment_status_code_enum",
            length=30,
        ),
        nullable=True,
    )
    household_type_code: Mapped[HouseholdTypeCode | None] = mapped_column(
        varchar_enum(
            HouseholdTypeCode,
            name="household_type_code_enum",
            length=30,
        ),
        nullable=True,
    )
    household_size: Mapped[int | None] = mapped_column(
        SMALLINT_UNSIGNED,
        nullable=True,
    )
    housing_type_code: Mapped[HousingTypeCode | None] = mapped_column(
        varchar_enum(
            HousingTypeCode,
            name="housing_type_code_enum",
            length=30,
        ),
        nullable=True,
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    user: Mapped[User] = relationship(back_populates="profile")


class UserConsent(TimestampMixin, Base):
    """Versioned privacy/terms consent audit record."""

    __tablename__ = "user_consents"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "consent_type",
            "consent_version",
            name="uk_user_consent_version",
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
    consent_type: Mapped[ConsentType] = mapped_column(
        varchar_enum(
            ConsentType,
            name="consent_type_enum",
            length=50,
        ),
        nullable=False,
    )
    consent_version: Mapped[str] = mapped_column(String(30), nullable=False)
    is_agreed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    agreed_at: Mapped[datetime | None] = mapped_column(
        DATETIME_FSP6,
        nullable=True,
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(
        DATETIME_FSP6,
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="consents")


__all__ = [
    "AccountStatus",
    "ConsentType",
    "EmploymentStatusCode",
    "HouseholdTypeCode",
    "HousingTypeCode",
    "IncomeBandCode",
    "User",
    "UserConsent",
    "UserProfile",
]
