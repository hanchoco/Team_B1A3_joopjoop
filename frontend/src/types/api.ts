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
  calculation_rule_json: unknown
  display_text: string | null
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

// Simulator DTOs (see backend/app/schemas/simulator.py). Money/percentage
// fields are plain numbers over the wire.

export type SimulatorCategory =
  | 'HOUSING'
  | 'TRANSPORT'
  | 'FINANCE'
  | 'TAX'
  | 'EMPLOYMENT'
  | 'WELFARE'

export interface SimulatorResult {
  category: SimulatorCategory
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

export interface HousingSimulatorRequest {
  monthly_rent_amount: number
  monthly_management_fee_amount?: number
  deposit_amount?: number
  monthly_support_amount: number
  support_months?: number
}

export interface TransportSimulatorRequest {
  monthly_transport_cost_amount: number
  reimbursement_rate_percent: number
  monthly_support_cap_amount?: number | null
  support_months?: number
}

export interface FinanceSimulatorRequest {
  principal_amount: number
  annual_interest_rate_percent: number
  interest_reduction_rate_percent: number
  support_months?: number
}

export interface TaxSimulatorRequest {
  annual_tax_amount: number
  tax_reduction_rate_percent: number
  max_reduction_amount?: number | null
  support_months?: number
}

export interface EmploymentSimulatorRequest {
  monthly_income_amount: number
  monthly_subsidy_amount: number
  support_months?: number
}

export interface WelfareSimulatorRequest {
  monthly_living_cost_amount: number
  monthly_benefit_amount: number
  support_months?: number
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
