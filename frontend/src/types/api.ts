// Backend DTOs (see backend/app/schemas/user.py). Only the auth-flow subset
// needed for now — more are added as later features get wired up.

export type AccountStatus = 'ACTIVE' | 'SUSPENDED' | 'WITHDRAWN'

export interface UserResponse {
  id: number
  email: string
  nickname: string | null
  account_status: AccountStatus
  last_login_at: string | null
  created_at: string
  updated_at: string
}

export interface NotificationSettingResponse {
  notification_enabled: boolean
  deadline_d7_enabled: boolean
  deadline_d3_enabled: boolean
  deadline_d0_enabled: boolean
  email_enabled: boolean
  push_enabled: boolean
  user_id: number
  updated_at: string
}

export type NotificationSettingUpdatePayload = Partial<
  Pick<
    NotificationSettingResponse,
    'notification_enabled' | 'deadline_d7_enabled' | 'deadline_d3_enabled' | 'deadline_d0_enabled'
  >
>

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserResponse
}

export type ConsentType =
  | 'TERMS_REQUIRED'
  | 'PRIVACY_REQUIRED'
  | 'MARKETING_OPTIONAL'
  | 'THIRD_PARTY_OPTIONAL'

export interface ConsentCreate {
  consent_type: ConsentType
  consent_version: string
  is_agreed: boolean
}

export interface ConsentResponse extends ConsentCreate {
  id: number
  user_id: number
  agreed_at: string | null
  withdrawn_at: string | null
  created_at: string
  updated_at: string
}

export interface SignupRequest {
  email: string
  password: string
  nickname?: string
  consents?: ConsentCreate[]
}

export interface LoginRequest {
  email: string
  password: string
}

export interface ApiErrorBody {
  code: string
  detail: string
}

// Policy DTOs (see backend/app/schemas/policy.py).

export type PolicySource = 'ONTONG_YOUTH' | 'MANUAL'
export type PolicyStatus = 'DRAFT' | 'ACTIVE' | 'CLOSED' | 'ARCHIVED'
export type EligibilityStatus = 'ELIGIBLE' | 'NEEDS_REVIEW' | 'INELIGIBLE'
export type ConditionStatus = '충족' | '추가 확인 필요' | '불충족'

export interface PolicyCategoryResponse {
  id: number
  code: string
  name: string
  is_primary: boolean
}

export interface PolicySummaryResponse {
  id: number
  source: PolicySource
  title: string
  summary: string | null
  provider_name: string | null
  application_start_date: string | null
  application_end_date: string | null
  is_ongoing: boolean
  published_date: string | null
  status: PolicyStatus
  subcategory: string | null
  region_scope: string | null
  categories: PolicyCategoryResponse[]
  card_status: EligibilityStatus | null
  match_score: number | string | null
  estimated_benefit_amount: number | string | null
  max_benefit_amount: number | string | null
  days_until_deadline: number | null
  is_bookmarked: boolean
  is_simulatable: boolean
}

export interface PolicyConditionResponse {
  id: number
  policy_id: number
  condition_key: string
  operator: string
  expected_value_json: unknown
  condition_group_no: number
  is_required: boolean
  check_mode: 'AUTO' | 'MANUAL' | 'DOCUMENT'
  description: string
  failure_message: string | null
  sort_order: number
  created_at: string
  updated_at: string
}

export interface PolicyBenefitResponse {
  id: number
  policy_id: number
  benefit_type: string
  amount_type: string
  min_amount: number | string | null
  max_amount: number | string | null
  payment_cycle: string | null
  duration_months: number | null
  max_total_amount: number | string | null
  calculation_rule_json: CalcRuleJson | null
  display_text: string | null
  // Not a DB field - resolved server-side from benefit_type + policy category
  // (see backend services/policy_engine/calc_type.py). Tells the frontend
  // which simulator form/calculation_rule_json shape applies, if any.
  calc_type: CalcType | null
  created_at: string
  updated_at: string
}

export interface PolicyDocumentResponse {
  id: number
  policy_id: number
  document_code: string
  document_name: string
  required_reason: string | null
  issuing_organization: string | null
  issuing_method: string | null
  issuing_url: string | null
  submission_format: string | null
  is_required: boolean
  display_order: number
  created_at: string
  updated_at: string
}

export interface PolicyDetailResponse extends PolicySummaryResponse {
  description: string | null
  support_target_text: string | null
  support_content_text: string | null
  application_method: string | null
  application_url: string | null
  contact: string | null
  conditions: PolicyConditionResponse[]
  benefits: PolicyBenefitResponse[]
  documents: PolicyDocumentResponse[]
  created_at: string
  updated_at: string
}

export interface PolicyListResponse {
  items: PolicySummaryResponse[]
  total: number
  page: number
  size: number
}

export interface DashboardUpcomingPolicy {
  policy_id: number
  title: string
  summary: string | null
  application_end_date: string
  days_until_deadline: number
}

export interface DashboardSummaryResponse {
  upcoming_deadline_policy: DashboardUpcomingPolicy | null
  upcoming_deadline_count: number
  missed_benefit_total_amount: number | string
  missed_benefit_policy_count: number
}

export interface PolicyConditionResultResponse {
  condition_id: number
  condition_key: string
  description: string
  status: ConditionStatus
  actual_value_json: unknown
  reason: string | null
  check_mode: 'AUTO' | 'MANUAL' | 'DOCUMENT'
  is_user_confirmed: boolean
  confirmed_at: string | null
  evaluated_at: string | null
}

export interface PolicyMatchDetailResponse {
  id: number | null
  user_id: number
  policy_id: number
  card_status: EligibilityStatus
  match_score: number | string
  satisfied_condition_count: number
  review_condition_count: number
  failed_condition_count: number
  total_condition_count: number
  estimated_benefit_amount: number | string | null
  engine_version: string
  evaluated_at: string
  conditions: PolicyConditionResultResponse[]
}

export interface PolicyBookmarkResponse {
  policy_id: number
  is_bookmarked: boolean
  bookmarked_at: string | null
}

export interface CategoryResponse {
  id: number
  code: string
  name: string
  description: string | null
  display_order: number
  is_active: boolean
  questions: unknown[]
}

export type AnswerType = 'SINGLE_SELECT' | 'MULTI_SELECT' | 'NUMBER' | 'BOOLEAN' | 'TEXT' | 'DATE'

export interface CategoryQuestionResponse {
  id: number
  category_id: number
  question_key: string
  label: string
  description: string | null
  answer_type: AnswerType
  options_json: unknown
  unit: string | null
  is_required: boolean
  is_used_for_matching: boolean
  display_order: number
  is_active: boolean
}

export interface CategoryAnswerUpsert {
  question_id: number
  answer_json: { value: unknown }
}

export interface CategoryAnswerResponse extends CategoryAnswerUpsert {
  id: number
  user_id: number
  answered_at: string
  updated_at: string
}

// Simulator DTOs (see backend/app/schemas/simulator.py,
// backend/app/models/policy.py:CalcType, docs/simulator_calc_rules.md).
// Money/percentage fields are plain numbers over the wire.

export type CalcType =
  | 'LOAN_INTEREST'
  | 'SAVINGS_ASSET'
  | 'CASH_VOUCHER'
  | 'HOUSING_RENT'
  | 'EMPLOYMENT_EDUCATION'
  | 'TAX_DEDUCTION'

// calculation_rule_json shapes the policy already knows (docs/simulator_calc_rules.md).
// These are read-only display values - never rendered as editable inputs.

export interface LoanInterestRuleJson {
  policy_interest_rate_percent: number
  interest_reduction_rate_percent?: number
  max_loan_amount: number
  max_support_months: number
  repayment_type: string
}

export interface SavingsAssetRuleJson {
  government_match_rate_percent: number
  monthly_max_support_amount: number
  maturity_months: number
  base_interest_rate_percent: number
  bonus_interest_rate_percent?: number
}

export interface CashVoucherFixedRuleJson {
  amount_type: 'FIXED'
  amount: number
  payment_cycle: string
  max_count: number
}

export interface CashVoucherPercentageRuleJson {
  amount_type: 'PERCENTAGE'
  rate_percent: number
  cap_amount: number
  payment_cycle: string
}

export type CashVoucherRuleJson = CashVoucherFixedRuleJson | CashVoucherPercentageRuleJson

export interface HousingRentRuleJson {
  monthly_support_cap_amount: number
  support_months: number
  deposit_limit_amount?: number
  rent_limit_amount?: number
}

export interface EmploymentEducationRuleJson {
  training_allowance_amount?: number
  education_subsidy_amount?: number
  employment_success_bonus_amount?: number
  support_months: number
}

export interface TaxDeductionRuleJson {
  deduction_rate_percent: number
  max_deduction_amount?: number
  deduction_type: 'TAX_CREDIT' | 'INCOME_DEDUCTION'
}

export type CalcRuleJson =
  | LoanInterestRuleJson
  | SavingsAssetRuleJson
  | CashVoucherRuleJson
  | HousingRentRuleJson
  | EmploymentEducationRuleJson
  | TaxDeductionRuleJson

export interface SimulatorResult {
  category: CalcType
  monthly_before_amount: number | string
  monthly_after_amount: number | string
  monthly_savings_amount: number | string
  annual_before_amount: number | string
  annual_after_amount: number | string
  annual_savings_amount: number | string
  total_benefit_amount: number | string
  support_months: number
  breakdown: Record<string, number | string>
  disclaimer: string
}

// Transient per-request personal variables only - never persisted, and never
// includes fields already known from calculation_rule_json.
export interface SimulateBenefitRequest {
  user_input: Record<string, number>
}

// Checklist DTOs (see backend/app/schemas/checklist.py).

export type PreparationStatus = 'NOT_STARTED' | 'PREPARING' | 'READY' | 'SUBMITTED'

// Cached condition-check result for the checklist screen. This is a
// separate, English-valued cache enum from the live ConditionStatus used on
// the policy detail page (see AGENTS.md 4번) — do not conflate the two.
export type ConditionResultStatus = 'SATISFIED' | 'NEEDS_REVIEW' | 'UNSATISFIED'

export interface ChecklistConditionItem {
  condition_id: number
  condition_key: string
  description: string
  result_status: ConditionResultStatus
  reason: string
  is_user_confirmed: boolean
  confirmed_at: string | null
}

export interface ChecklistDocumentItem {
  document_id: number
  document_code: string
  document_name: string
  required_reason: string | null
  issuing_organization: string | null
  issuing_method: string | null
  issuing_url: string | null
  submission_format: string | null
  is_required: boolean
  preparation_status: PreparationStatus
  is_checked: boolean
  checked_at: string | null
  note: string | null
}

export interface ChecklistResponse {
  state_id: number
  policy_id: number
  policy_title: string
  preparation_status: PreparationStatus
  progress_percent: number
  conditions: ChecklistConditionItem[]
  documents: ChecklistDocumentItem[]
}

export interface DocumentProgressUpdate {
  preparation_status: PreparationStatus
  is_checked: boolean
  note?: string | null
}

export interface ConditionConfirmationUpdate {
  confirmed: boolean
}

// Chatbot DTOs (see backend/app/schemas/chatbot.py). Stateless — no chat
// history is persisted server-side.

export interface PolicyQuestionRequest {
  question: string
}

export interface PolicyQuestionResponse {
  answer: string
  suggested_questions: string[]
}

// User profile DTOs (see backend/app/schemas/user.py, models/user.py).

export type IncomeBandCode =
  | 'BELOW_50'
  | 'BETWEEN_50_75'
  | 'BETWEEN_75_100'
  | 'BETWEEN_100_120'
  | 'BETWEEN_120_150'
  | 'ABOVE_150'
  | 'UNKNOWN'

export type EmploymentStatusCode =
  | 'EMPLOYED'
  | 'SELF_EMPLOYED'
  | 'UNEMPLOYED'
  | 'JOB_SEEKER'
  | 'STUDENT'
  | 'ON_LEAVE'
  | 'OTHER'

export type HouseholdTypeCode =
  | 'SINGLE'
  | 'COUPLE'
  | 'WITH_PARENTS'
  | 'SINGLE_PARENT'
  | 'MULTI_PERSON'
  | 'OTHER'

export type HousingTypeCode =
  | 'OWNED'
  | 'JEONSE'
  | 'MONTHLY_RENT'
  | 'PUBLIC_RENTAL'
  | 'DORMITORY'
  | 'WITH_FAMILY'
  | 'OTHER'

export interface UserProfileFields {
  birth_year?: number | null
  region_code?: string | null
  region_sido?: string | null
  region_sigungu?: string | null
  income_band_code?: IncomeBandCode | null
  employment_status_code?: EmploymentStatusCode | null
  household_type_code?: HouseholdTypeCode | null
  household_size?: number | null
  housing_type_code?: HousingTypeCode | null
}

export interface UserProfileUpdate extends UserProfileFields {
  onboarding_completed?: boolean | null
}

export interface UserProfileResponse extends UserProfileFields {
  user_id: number
  onboarding_completed: boolean
  created_at: string
  updated_at: string
}

// My Policies DTOs (see backend/app/schemas/checklist.py: UserPolicyItemResponse).

export type MyPoliciesTab = 'bookmarked' | 'preparing' | 'applied'

export interface UserPolicyItemResponse {
  state_id: number
  policy_id: number
  title: string
  summary: string | null
  category_code: string | null
  application_end_date: string | null
  is_bookmarked: boolean
  preparation_status: PreparationStatus
  progress_percent: number
  application_status: string
  application_date: string | null
  match_score: number | string | null
  eligibility_status: EligibilityStatus | null
  updated_at: string
}
