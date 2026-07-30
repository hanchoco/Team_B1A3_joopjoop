import apiClient from './client'

export type DocumentPreparationStatus = 'NOT_STARTED' | 'PREPARING' | 'READY' | 'SUBMITTED'
export type ApplicationStatus =
  'NOT_APPLIED' | 'SUBMITTED' | 'UNDER_REVIEW' | 'APPROVED' | 'REJECTED' | 'PAID'
export type PreparationStatus = 'NOT_STARTED' | 'IN_PROGRESS' | 'COMPLETED'

export interface ChecklistCondition {
  condition_id: number
  condition_key: string
  description: string
  result_status: string
  reason: string
  is_user_confirmed: boolean
  confirmed_at: string | null
}

export interface ChecklistDocument {
  document_id: number
  document_code: string
  document_name: string
  required_reason: string | null
  issuing_organization: string | null
  issuing_method: string | null
  issuing_url: string | null
  submission_format: string | null
  is_required: boolean
  preparation_status: DocumentPreparationStatus
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
  conditions: ChecklistCondition[]
  documents: ChecklistDocument[]
}

export interface UserPolicyItem {
  state_id: number
  policy_id: number
  title: string
  summary: string | null
  application_end_date: string | null
  is_bookmarked: boolean
  preparation_status: PreparationStatus
  progress_percent: number
  application_status: ApplicationStatus
  application_date: string | null
  match_score: string | number | null
  eligibility_status: string | null
  updated_at: string
}

export type MyPolicyTab = 'bookmarked' | 'preparing' | 'applied'
export type MyPolicySort = 'recommendation' | 'latest' | 'deadline'

export async function startPolicyPreparation(policyId: number): Promise<ChecklistResponse> {
  const { data } = await apiClient.post<ChecklistResponse>(
    `/api/v1/policies/${policyId}/preparation`,
  )
  return data
}

export async function updateChecklistDocument(
  stateId: number,
  documentId: number,
  payload: {
    preparation_status: DocumentPreparationStatus
    is_checked: boolean
    note?: string | null
  },
): Promise<ChecklistResponse> {
  const { data } = await apiClient.patch<ChecklistResponse>(
    `/api/v1/preparations/${stateId}/documents/${documentId}`,
    payload,
  )
  return data
}

export async function confirmChecklistCondition(
  stateId: number,
  conditionId: number,
  confirmed: boolean,
): Promise<ChecklistResponse> {
  const { data } = await apiClient.patch<ChecklistResponse>(
    `/api/v1/preparations/${stateId}/conditions/${conditionId}`,
    { confirmed },
  )
  return data
}

export async function recordPolicyApplication(
  policyId: number,
  applicationDate: string,
): Promise<UserPolicyItem> {
  const { data } = await apiClient.post<UserPolicyItem>(
    `/api/v1/policies/${policyId}/applications`,
    {
      application_date: applicationDate,
      application_status: 'SUBMITTED',
    },
  )
  return data
}

export async function getMyPolicies(
  tab?: MyPolicyTab,
  sort: MyPolicySort = 'latest',
): Promise<UserPolicyItem[]> {
  const { data } = await apiClient.get<UserPolicyItem[]>('/api/v1/users/me/policies', {
    params: { tab, sort },
  })
  return data
}
