"""Preparation checklist and My Policies schemas."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DocumentProgressUpdate(BaseModel):
    """One document preparation update."""

    preparation_status: str = Field(pattern="^(NOT_STARTED|PREPARING|READY|SUBMITTED)$")
    is_checked: bool
    note: str | None = Field(default=None, max_length=500)


class ConditionConfirmationUpdate(BaseModel):
    """User confirmation for a manual condition."""

    confirmed: bool


class ApplicationCreate(BaseModel):
    """Application history entry."""

    application_date: date
    application_status: str = Field(
        default="SUBMITTED",
        pattern="^(SUBMITTED|UNDER_REVIEW|APPROVED|REJECTED|PAID)$",
    )
    application_note: str | None = Field(default=None, max_length=500)


class ChecklistConditionItem(BaseModel):
    """Condition result shown above the document checklist."""

    condition_id: int
    condition_key: str
    description: str
    result_status: str
    reason: str
    is_user_confirmed: bool
    confirmed_at: datetime | None


class ChecklistDocumentItem(BaseModel):
    """Document definition and the user's current preparation state."""

    document_id: int
    document_code: str
    document_name: str
    required_reason: str | None
    issuing_organization: str | None
    issuing_method: str | None
    issuing_url: str | None
    submission_format: str | None
    is_required: bool
    preparation_status: str
    is_checked: bool
    checked_at: datetime | None
    note: str | None


class ChecklistResponse(BaseModel):
    """Resumable preparation screen payload."""

    state_id: int
    policy_id: int
    policy_title: str
    preparation_status: str
    progress_percent: int
    conditions: list[ChecklistConditionItem]
    documents: list[ChecklistDocumentItem]


class UserPolicyItemResponse(BaseModel):
    """One My Policies card."""

    state_id: int
    policy_id: int
    title: str
    summary: str | None
    application_end_date: date | None
    is_bookmarked: bool
    preparation_status: str
    progress_percent: int
    application_status: str
    application_date: date | None
    match_score: Decimal | None
    eligibility_status: str | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
