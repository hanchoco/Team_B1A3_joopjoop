"""Pydantic v2 DTOs for policy lists, details, matching, and preparation."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from app.models.policy import (
    AmountType,
    BenefitType,
    CalcType,
    PaymentCycle,
    PolicySource,
    PolicyStatus,
)
from app.models.policy_condition import CheckMode, ConditionOperator
from app.models.user_category_profile import CategoryCode
from app.models.user_document_progress import DocumentPreparationStatus
from app.models.user_policy import (
    ApplicationStatus,
    EligibilityStatus,
    PreparationStatus,
)


class ConditionStatus(str, Enum):
    """Condition-level status used only on policy detail/checklist screens."""

    SATISFIED = "충족"
    NEEDS_REVIEW = "추가 확인 필요"
    UNSATISFIED = "불충족"


class PolicySort(str, Enum):
    """Supported policy list sort orders."""

    RECOMMENDATION = "recommendation"
    LATEST = "latest"
    DEADLINE = "deadline"


class SchemaModel(BaseModel):
    """Strict ORM-compatible DTO base."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class PolicyCategoryResponse(SchemaModel):
    """Category attached to a policy."""

    id: int
    code: CategoryCode
    name: str
    is_primary: bool = False


class PolicyBenefitFields(SchemaModel):
    """Shared structured policy benefit fields."""

    benefit_type: BenefitType
    amount_type: AmountType
    min_amount: Decimal | None = Field(default=None, ge=0)
    max_amount: Decimal | None = Field(default=None, ge=0)
    payment_cycle: PaymentCycle | None = None
    duration_months: int | None = Field(default=None, ge=1)
    max_total_amount: Decimal | None = Field(default=None, ge=0)
    calculation_rule_json: dict[str, JsonValue] | None = None
    display_text: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_amount_range(self) -> PolicyBenefitFields:
        """Ensure an optional benefit range is ordered."""

        if (
            self.min_amount is not None
            and self.max_amount is not None
            and self.min_amount > self.max_amount
        ):
            raise ValueError("min_amount cannot be greater than max_amount")
        return self


class PolicyBenefitCreate(PolicyBenefitFields):
    """Structured benefit accepted by policy ingestion/admin flows."""


class PolicyBenefitResponse(PolicyBenefitFields):
    """Persisted benefit definition."""

    id: int
    policy_id: int
    # Not a DB column - resolved at read time via
    # services.policy_engine.calc_type.resolve_calc_type() so the frontend
    # knows which simulator form/calculation_rule_json shape applies.
    calc_type: CalcType | None = None
    created_at: datetime
    updated_at: datetime


class PolicyConditionFields(SchemaModel):
    """Shared confirmed eligibility condition fields."""

    condition_key: str = Field(min_length=1, max_length=100)
    operator: ConditionOperator
    expected_value_json: JsonValue | None = None
    condition_group_no: int = Field(default=1, ge=1)
    is_required: bool = True
    check_mode: CheckMode = CheckMode.AUTO
    description: str = Field(min_length=1, max_length=500)
    failure_message: str | None = Field(default=None, max_length=500)
    sort_order: int = Field(default=0, ge=0)


class PolicyConditionCreate(PolicyConditionFields):
    """Confirmed condition accepted after AI extraction review."""


class PolicyConditionResponse(PolicyConditionFields):
    """Persisted condition definition without user-specific evaluation."""

    id: int
    policy_id: int
    created_at: datetime
    updated_at: datetime


class PolicyDocumentFields(SchemaModel):
    """Shared application-document fields."""

    document_code: str = Field(min_length=1, max_length=50)
    document_name: str = Field(min_length=1, max_length=255)
    required_reason: str | None = Field(default=None, max_length=500)
    issuing_organization: str | None = Field(default=None, max_length=255)
    issuing_method: str | None = Field(default=None, max_length=500)
    issuing_url: str | None = Field(default=None, max_length=1000)
    submission_format: str | None = Field(default=None, max_length=100)
    is_required: bool = True
    display_order: int = Field(default=0, ge=0)


class PolicyDocumentCreate(PolicyDocumentFields):
    """Confirmed checklist document accepted after AI-output review."""


class PolicyDocumentResponse(PolicyDocumentFields):
    """Persisted policy checklist document."""

    id: int
    policy_id: int
    created_at: datetime
    updated_at: datetime


class PolicyCreate(SchemaModel):
    """Policy ingestion payload used by integration/admin services."""

    source: PolicySource = PolicySource.MANUAL
    external_id: str | None = Field(default=None, max_length=100)
    title: str = Field(min_length=1, max_length=255)
    summary: str | None = Field(default=None, max_length=500)
    description: str | None = None
    support_target_text: str | None = None
    support_content_text: str | None = None
    application_method: str | None = None
    provider_name: str | None = Field(default=None, max_length=255)
    application_url: str | None = Field(default=None, max_length=1000)
    application_start_date: date | None = None
    application_end_date: date | None = None
    is_ongoing: bool = False
    published_date: date | None = None
    status: PolicyStatus = PolicyStatus.DRAFT
    raw_payload: dict[str, JsonValue] | None = None
    source_updated_at: datetime | None = None
    subcategory: str | None = Field(default=None, max_length=100)
    region_scope: str | None = Field(default=None, max_length=20)
    region_code: str | None = Field(default=None, max_length=20)
    contact: str | None = Field(default=None, max_length=255)
    original_text: str | None = None
    is_active: bool = True
    category_ids: list[int] = Field(default_factory=list)
    benefits: list[PolicyBenefitCreate] = Field(default_factory=list)
    conditions: list[PolicyConditionCreate] = Field(default_factory=list)
    documents: list[PolicyDocumentCreate] = Field(default_factory=list)


class PolicyUpdate(SchemaModel):
    """Partial policy metadata update."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    summary: str | None = Field(default=None, max_length=500)
    description: str | None = None
    support_target_text: str | None = None
    support_content_text: str | None = None
    application_method: str | None = None
    provider_name: str | None = Field(default=None, max_length=255)
    application_url: str | None = Field(default=None, max_length=1000)
    application_start_date: date | None = None
    application_end_date: date | None = None
    is_ongoing: bool | None = None
    published_date: date | None = None
    status: PolicyStatus | None = None
    source_updated_at: datetime | None = None
    subcategory: str | None = Field(default=None, max_length=100)
    region_scope: str | None = Field(default=None, max_length=20)
    region_code: str | None = Field(default=None, max_length=20)
    contact: str | None = Field(default=None, max_length=255)
    original_text: str | None = None
    is_active: bool | None = None


class PolicySummaryResponse(SchemaModel):
    """Policy card used by lists, recommendations, and dashboard summaries."""

    id: int
    source: PolicySource
    title: str
    summary: str | None = None
    provider_name: str | None = None
    application_start_date: date | None = None
    application_end_date: date | None = None
    is_ongoing: bool
    published_date: date | None = None
    status: PolicyStatus
    subcategory: str | None = None
    region_scope: str | None = None
    categories: list[PolicyCategoryResponse] = Field(default_factory=list)
    card_status: EligibilityStatus | None = None
    match_score: Decimal | None = Field(default=None, ge=0, le=100)
    estimated_benefit_amount: Decimal | None = Field(default=None, ge=0)
    max_benefit_amount: Decimal | None = Field(default=None, ge=0)
    days_until_deadline: int | None = None
    is_bookmarked: bool = False
    is_simulatable: bool = False


class PolicyDetailResponse(PolicySummaryResponse):
    """Full policy detail plus confirmed conditions and documents."""

    description: str | None = None
    support_target_text: str | None = None
    support_content_text: str | None = None
    application_method: str | None = None
    application_url: str | None = None
    contact: str | None = None
    conditions: list[PolicyConditionResponse] = Field(default_factory=list)
    benefits: list[PolicyBenefitResponse] = Field(default_factory=list)
    documents: list[PolicyDocumentResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PolicyConditionResultResponse(SchemaModel):
    """User-specific evaluation for one policy condition."""

    condition_id: int
    condition_key: str
    description: str
    status: ConditionStatus
    actual_value_json: JsonValue | None = None
    reason: str | None = None
    check_mode: CheckMode
    is_user_confirmed: bool = False
    confirmed_at: datetime | None = None
    evaluated_at: datetime | None = None


class PolicyMatchResponse(SchemaModel):
    """Card-level cached evaluation summary."""

    id: int | None = None
    user_id: int
    policy_id: int
    card_status: EligibilityStatus
    match_score: Decimal = Field(ge=0, le=100)
    satisfied_condition_count: int = Field(ge=0)
    review_condition_count: int = Field(ge=0)
    failed_condition_count: int = Field(ge=0)
    total_condition_count: int = Field(ge=0)
    estimated_benefit_amount: Decimal | None = Field(default=None, ge=0)
    engine_version: str
    evaluated_at: datetime


class PolicyMatchDetailResponse(PolicyMatchResponse):
    """Card evaluation plus condition-level details."""

    conditions: list[PolicyConditionResultResponse] = Field(default_factory=list)


class PolicyListResponse(SchemaModel):
    """Paginated policy card collection."""

    items: list[PolicySummaryResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1)


class PolicyListQuery(SchemaModel):
    """Validated policy list filters."""

    category_code: CategoryCode | None = None
    card_status: EligibilityStatus | None = None
    sort: PolicySort = PolicySort.RECOMMENDATION
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    keyword: str | None = Field(default=None, min_length=1, max_length=100)


class PolicyStateResponse(SchemaModel):
    """Persisted bookmark/preparation/application state."""

    id: int
    user_id: int
    policy_id: int
    is_bookmarked: bool
    bookmarked_at: datetime | None = None
    preparation_status: PreparationStatus
    preparation_started_at: datetime | None = None
    preparation_completed_at: datetime | None = None
    progress_percent: int = Field(ge=0, le=100)
    application_status: ApplicationStatus
    application_date: date | None = None
    application_note: str | None = None
    created_at: datetime
    updated_at: datetime


class PolicyBookmarkResponse(SchemaModel):
    """Result of adding/removing a policy bookmark."""

    policy_id: int
    is_bookmarked: bool
    bookmarked_at: datetime | None = None


class DocumentProgressUpdate(SchemaModel):
    """Partial document checklist update."""

    preparation_status: DocumentPreparationStatus | None = None
    is_checked: bool | None = None
    note: str | None = Field(default=None, max_length=500)


class DocumentProgressResponse(SchemaModel):
    """Persisted checklist progress for one policy document."""

    id: int
    user_policy_state_id: int
    document_id: int
    preparation_status: DocumentPreparationStatus
    is_checked: bool
    checked_at: datetime | None = None
    note: str | None = None
    updated_at: datetime


class ConditionConfirmationUpdate(SchemaModel):
    """Manual confirmation for a condition requiring user review."""

    is_confirmed: bool


class ApplicationCreate(SchemaModel):
    """Mark a policy application as submitted."""

    application_date: date
    application_note: str | None = Field(default=None, max_length=500)
    application_status: ApplicationStatus = ApplicationStatus.SUBMITTED


class ChecklistConditionItem(PolicyConditionResultResponse):
    """Condition row in the preparation checklist."""


class ChecklistDocumentItem(PolicyDocumentResponse):
    """Document definition together with the current user's progress."""

    progress: DocumentProgressResponse | None = None


class ChecklistResponse(SchemaModel):
    """Complete resumable preparation checklist."""

    state: PolicyStateResponse
    policy_id: int
    policy_title: str
    progress_percent: int = Field(ge=0, le=100)
    conditions: list[ChecklistConditionItem] = Field(default_factory=list)
    documents: list[ChecklistDocumentItem] = Field(default_factory=list)


PolicyCard = PolicySummaryResponse
PolicyDetail = PolicyDetailResponse
ConditionEvaluation = PolicyConditionResultResponse
PreparationStartResponse = PolicyStateResponse


__all__ = [
    "ApplicationCreate",
    "ChecklistConditionItem",
    "ChecklistDocumentItem",
    "ChecklistResponse",
    "ConditionConfirmationUpdate",
    "ConditionEvaluation",
    "ConditionStatus",
    "DocumentProgressResponse",
    "DocumentProgressUpdate",
    "PolicyBenefitCreate",
    "PolicyBenefitResponse",
    "PolicyBookmarkResponse",
    "PolicyCard",
    "PolicyCategoryResponse",
    "PolicyConditionCreate",
    "PolicyConditionResponse",
    "PolicyConditionResultResponse",
    "PolicyCreate",
    "PolicyDetail",
    "PolicyDetailResponse",
    "PolicyDocumentCreate",
    "PolicyDocumentResponse",
    "PolicyListQuery",
    "PolicyListResponse",
    "PolicyMatchDetailResponse",
    "PolicyMatchResponse",
    "PolicySort",
    "PolicyStateResponse",
    "PolicySummaryResponse",
    "PolicyUpdate",
    "PreparationStartResponse",
]
