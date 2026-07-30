import type { BackendEligibilityStatus, EligibilityStatus } from '../types/policy'
import { toEligibilityStatus } from '../types/policy'
import apiClient from './client'

export type PolicySort = 'recommendation' | 'latest' | 'deadline'

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

type PolicySummaryApiResponse = Omit<PolicySummary, 'card_status'> & {
  card_status?: EligibilityStatus | BackendEligibilityStatus | null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function extractPolicyItems(payload: unknown): unknown[] {
  if (Array.isArray(payload)) return payload
  if (!isRecord(payload)) return []

  if (Array.isArray(payload.items)) return payload.items
  if (Array.isArray(payload.policies)) return payload.policies
  if (Array.isArray(payload.data)) return payload.data

  if (isRecord(payload.data)) {
    if (Array.isArray(payload.data.items)) return payload.data.items
    if (Array.isArray(payload.data.policies)) return payload.data.policies
    if (Array.isArray(payload.data.data)) return payload.data.data
  }

  return []
}

function getResponseMetadata(payload: unknown): Record<string, unknown> {
  if (!isRecord(payload)) return {}
  return isRecord(payload.data) ? { ...payload, ...payload.data } : payload
}

function normalizePolicySummary(policy: PolicySummaryApiResponse): PolicySummary {
  const cardStatus = policy.card_status ?? null
  return {
    ...policy,
    categories: Array.isArray(policy.categories) ? policy.categories : [],
    card_status: toEligibilityStatus(cardStatus),
  }
}

export async function getRecommendedPolicies(
  params: PolicyListParams = {},
): Promise<PolicyListResponse> {
  const requestParams =
    params.eligibility_status === 'INELIGIBLE'
      ? { ...params, eligibility_status: undefined }
      : params
  const { data } = await apiClient.get<unknown>('/api/v1/policies', {
    params: requestParams,
  })
  const metadata = getResponseMetadata(data)
  const items = extractPolicyItems(data)
    .filter(isRecord)
    .map((policy) => normalizePolicySummary(policy as unknown as PolicySummaryApiResponse))
  const response: PolicyListResponse = {
    items,
    total: typeof metadata.total === 'number' ? metadata.total : items.length,
    page: typeof metadata.page === 'number' ? metadata.page : (params.page ?? 1),
    size: typeof metadata.size === 'number' ? metadata.size : items.length,
  }
  if (params.eligibility_status !== 'INELIGIBLE') return response

  const ineligibleItems = items.filter((policy) => policy.card_status === 'INELIGIBLE')
  return { ...response, items: ineligibleItems, total: ineligibleItems.length }
}

export async function getPolicyDetail(policyId: number): Promise<PolicyDetail> {
  const { data } = await apiClient.get<unknown>(`/api/v1/policies/${policyId}`)
  const payload = isRecord(data) && isRecord(data.data) ? data.data : data
  if (!isRecord(payload)) throw new Error('Invalid policy detail response')

  const policy = normalizePolicySummary(
    payload as unknown as PolicySummaryApiResponse,
  ) as PolicyDetail
  return {
    ...policy,
    conditions: Array.isArray(policy.conditions) ? policy.conditions : [],
    benefits: Array.isArray(policy.benefits) ? policy.benefits : [],
    documents: Array.isArray(policy.documents) ? policy.documents : [],
  }
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
