"""Pydantic v2 DTOs for accounts, profiles, categories, and preferences."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from app.models.notification_setting import (
    NotificationSendStatus,
    NotificationType,
)
from app.models.user import (
    AccountStatus,
    ConsentType,
    EmploymentStatusCode,
    HouseholdTypeCode,
    HousingTypeCode,
    IncomeBandCode,
)
from app.models.user_category_profile import AnswerType, CategoryCode

EmailValue = Annotated[
    str,
    Field(
        min_length=5,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]
PasswordValue = Annotated[str, Field(min_length=8, max_length=128)]


class SchemaModel(BaseModel):
    """Strict base for request and response models."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class ConsentCreate(SchemaModel):
    """A consent choice captured during signup or settings changes."""

    consent_type: ConsentType
    consent_version: str = Field(min_length=1, max_length=30)
    is_agreed: bool


class ConsentResponse(ConsentCreate):
    """Persisted versioned consent record."""

    id: int
    user_id: int
    agreed_at: datetime | None = None
    withdrawn_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UserCreate(SchemaModel):
    """Signup request; plaintext passwords never appear in response DTOs."""

    email: EmailValue
    password: PasswordValue
    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    consents: list[ConsentCreate] = Field(default_factory=list)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Normalize the case-insensitive email identifier."""

        return value.lower()


class UserLogin(SchemaModel):
    """Email/password login request."""

    email: EmailValue
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Normalize the case-insensitive email identifier."""

        return value.lower()


class UserAccountUpdate(SchemaModel):
    """Editable account display and password fields."""

    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    current_password: str | None = Field(default=None, min_length=1, max_length=128)
    new_password: PasswordValue | None = None


class UserResponse(SchemaModel):
    """Public account representation."""

    id: int
    email: str
    nickname: str | None = None
    account_status: AccountStatus
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TokenResponse(SchemaModel):
    """Bearer token returned after signup/login."""

    access_token: str
    token_type: str = "bearer"


class UserProfileFields(SchemaModel):
    """Shared stable policy-matching profile fields."""

    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    region_code: str | None = Field(default=None, max_length=20)
    region_sido: str | None = Field(default=None, max_length=30)
    region_sigungu: str | None = Field(default=None, max_length=30)
    income_band_code: IncomeBandCode | None = None
    employment_status_code: EmploymentStatusCode | None = None
    household_type_code: HouseholdTypeCode | None = None
    household_size: int | None = Field(default=None, ge=1, le=50)
    housing_type_code: HousingTypeCode | None = None


class UserProfileCreate(UserProfileFields):
    """Initial onboarding profile.

    Monetary simulator inputs are intentionally absent because they are entered
    for every simulation and must not be persisted in ``user_profiles``.
    """

    onboarding_completed: bool = False


class UserProfileUpdate(UserProfileFields):
    """Partial profile update; callers should apply ``exclude_unset=True``."""

    onboarding_completed: bool | None = None


class UserProfileResponse(UserProfileFields):
    """Persisted matching profile."""

    user_id: int
    onboarding_completed: bool
    created_at: datetime
    updated_at: datetime


class UserWithProfileResponse(UserResponse):
    """Account together with the optional onboarding profile."""

    profile: UserProfileResponse | None = None


class CategoryQuestionResponse(SchemaModel):
    """Question metadata rendered by a category-specific onboarding form."""

    id: int
    category_id: int
    question_key: str
    label: str
    description: str | None = None
    answer_type: AnswerType
    options_json: JsonValue | None = None
    unit: str | None = None
    is_required: bool
    is_used_for_matching: bool
    display_order: int
    is_active: bool


class CategoryResponse(SchemaModel):
    """Policy category, optionally including its active questions."""

    id: int
    code: CategoryCode
    name: str
    description: str | None = None
    display_order: int
    is_active: bool
    questions: list[CategoryQuestionResponse] = Field(default_factory=list)


class CategoryAnswerUpsert(SchemaModel):
    """One category answer submitted by the current user."""

    question_id: int
    answer_json: dict[str, JsonValue]


class CategoryAnswersUpdate(SchemaModel):
    """Batch answer payload for one selected category."""

    answers: list[CategoryAnswerUpsert] = Field(min_length=1)


class CategoryAnswerResponse(CategoryAnswerUpsert):
    """Persisted category answer."""

    id: int
    user_id: int
    answered_at: datetime
    updated_at: datetime


class NotificationSettingUpdate(SchemaModel):
    """Partial update of notification/channel toggles."""

    notification_enabled: bool | None = None
    deadline_d7_enabled: bool | None = None
    deadline_d3_enabled: bool | None = None
    deadline_d0_enabled: bool | None = None
    email_enabled: bool | None = None
    push_enabled: bool | None = None


class NotificationSettingResponse(SchemaModel):
    """Current user's complete notification preferences."""

    user_id: int
    notification_enabled: bool
    deadline_d7_enabled: bool
    deadline_d3_enabled: bool
    deadline_d0_enabled: bool
    email_enabled: bool
    push_enabled: bool
    updated_at: datetime


class NotificationResponse(SchemaModel):
    """One in-app notification item."""

    id: int
    user_id: int
    policy_id: int | None = None
    notification_type: NotificationType
    title: str
    body: str
    scheduled_at: datetime
    sent_at: datetime | None = None
    read_at: datetime | None = None
    send_status: NotificationSendStatus


class NotificationReadResponse(SchemaModel):
    """Result of marking a notification as read."""

    id: int
    read_at: datetime


UserRead = UserResponse
UserProfileRead = UserProfileResponse


__all__ = [
    "CategoryAnswerResponse",
    "CategoryAnswerUpsert",
    "CategoryAnswersUpdate",
    "CategoryQuestionResponse",
    "CategoryResponse",
    "ConsentCreate",
    "ConsentResponse",
    "NotificationReadResponse",
    "NotificationResponse",
    "NotificationSettingResponse",
    "NotificationSettingUpdate",
    "TokenResponse",
    "UserAccountUpdate",
    "UserCreate",
    "UserLogin",
    "UserProfileCreate",
    "UserProfileRead",
    "UserProfileResponse",
    "UserProfileUpdate",
    "UserRead",
    "UserResponse",
    "UserWithProfileResponse",
]
