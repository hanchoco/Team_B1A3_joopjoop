import type { EligibilityStatus } from '../types'
import apiClient from './client'

export type PolicySort = 'recommendation' | 'latest' | 'deadline'
type BackendPolicyCardStatus = '가능성 높음' | '추가 확인 필요' | '불충족'

export interface PolicyCategory {
  id: number
  code: string
  name: string
  is_primary: boolean
}

export interface PolicySummary {
  id: number
  source: string
  title: string
  summary: string | null
  provider_name: string | null
  application_start_date: string | null
  application_end_date: string | null
  is_ongoing: boolean
  published_date: string | null
  status: string
  subcategory: string | null
  region_scope: string | null
  categories: PolicyCategory[]
  card_status: EligibilityStatus | null
  match_score: string | number | null
  estimated_benefit_amount: string | number | null
  max_benefit_amount: string | number | null
  days_until_deadline: number | null
  is_bookmarked: boolean
}

export interface PolicyCondition {
  id: number
  policy_id: number
  condition_key: string
  operator: string
  expected_value_json: unknown
  condition_group_no: number
  is_required: boolean
  check_mode: string
  description: string
  failure_message: string | null
  sort_order: number
  created_at: string
  updated_at: string
}

export interface PolicyBenefit {
  id: number
  policy_id: number
  benefit_type: string
  amount_type: string
  min_amount: string | number | null
  max_amount: string | number | null
  payment_cycle: string | null
  duration_months: number | null
  max_total_amount: string | number | null
  calculation_rule_json: Record<string, unknown> | null
  display_text: string | null
  created_at: string
  updated_at: string
}

export interface PolicyDocument {
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

export interface PolicyDetail extends PolicySummary {
  description: string | null
  support_target_text: string | null
  support_content_text: string | null
  application_method: string | null
  application_url: string | null
  contact: string | null
  conditions: PolicyCondition[]
  benefits: PolicyBenefit[]
  documents: PolicyDocument[]
  created_at: string
  updated_at: string
}

export interface PolicyListResponse {
  items: PolicySummary[]
  total: number
  page: number
  size: number
}

export interface PolicyListParams {
  category_code?: string
  eligibility_status?: EligibilityStatus
  sort?: PolicySort
  page?: number
  size?: number
  keyword?: string
}

export interface PolicyBookmarkResponse {
  policy_id: number
  is_bookmarked: boolean
  bookmarked_at: string | null
}

function normalizeCardStatus(
  status: EligibilityStatus | BackendPolicyCardStatus | null,
): EligibilityStatus | null {
  if (status === '가능성 높음') return 'ELIGIBLE'
  if (status === '추가 확인 필요') return 'NEEDS_REVIEW'
  if (status === '불충족') return 'INELIGIBLE'
  return status
}

function normalizePolicySummary<T extends PolicySummary>(policy: T): T {
  return { ...policy, card_status: normalizeCardStatus(policy.card_status) }
}

export async function getRecommendedPolicies(
  params: PolicyListParams = {},
): Promise<PolicyListResponse> {
  const requestParams =
    params.eligibility_status === 'INELIGIBLE'
      ? { ...params, eligibility_status: undefined }
      : params
  const { data } = await apiClient.get<PolicyListResponse>('/api/v1/policies', {
    params: requestParams,
  })
  const items = data.items.map(normalizePolicySummary)
  if (params.eligibility_status !== 'INELIGIBLE') return { ...data, items }

  const ineligibleItems = items.filter((policy) => policy.card_status === 'INELIGIBLE')
  return { ...data, items: ineligibleItems, total: ineligibleItems.length }
}

export async function getPolicyDetail(policyId: number): Promise<PolicyDetail> {
  const { data } = await apiClient.get<PolicyDetail>(`/api/v1/policies/${policyId}`)
  return normalizePolicySummary(data)
}

export async function addPolicyBookmark(policyId: number): Promise<PolicyBookmarkResponse> {
  const { data } = await apiClient.post<PolicyBookmarkResponse>(
    `/api/v1/policies/${policyId}/bookmark`,
  )
  return data
}

export async function removePolicyBookmark(policyId: number): Promise<void> {
  await apiClient.delete(`/api/v1/policies/${policyId}/bookmark`)
}
