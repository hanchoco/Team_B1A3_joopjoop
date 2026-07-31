import { apiClient } from './client'
import type {
  ChecklistResponse,
  ConditionConfirmationUpdate,
  DocumentProgressUpdate,
  MyPoliciesTab,
  UserPolicyItemResponse,
} from '../types/api'

export async function startPreparation(policyId: number): Promise<ChecklistResponse> {
  const response = await apiClient.post<ChecklistResponse>(`/policies/${policyId}/preparation`)
  return response.data
}

export async function updateChecklistDocument(
  stateId: number,
  documentId: number,
  payload: DocumentProgressUpdate,
): Promise<ChecklistResponse> {
  const response = await apiClient.patch<ChecklistResponse>(
    `/preparations/${stateId}/documents/${documentId}`,
    payload,
  )
  return response.data
}

export async function confirmChecklistCondition(
  stateId: number,
  conditionId: number,
  confirmed: boolean,
): Promise<ChecklistResponse> {
  const payload: ConditionConfirmationUpdate = { confirmed }
  const response = await apiClient.patch<ChecklistResponse>(
    `/preparations/${stateId}/conditions/${conditionId}`,
    payload,
  )
  return response.data
}

export async function resetChecklistProgress(
  checklist: ChecklistResponse,
): Promise<ChecklistResponse> {
  let updatedChecklist = checklist

  for (const condition of checklist.conditions) {
    if (condition.is_user_confirmed) {
      updatedChecklist = await confirmChecklistCondition(
        checklist.state_id,
        condition.condition_id,
        false,
      )
    }
  }

  for (const document of checklist.documents) {
    if (document.is_checked || document.preparation_status !== 'NOT_STARTED') {
      updatedChecklist = await updateChecklistDocument(checklist.state_id, document.document_id, {
        preparation_status: 'NOT_STARTED',
        is_checked: false,
        note: document.note,
      })
    }
  }

  return updatedChecklist
}

export async function recordPolicyApplication(
  policyId: number,
  applicationDate: string,
): Promise<UserPolicyItemResponse> {
  const response = await apiClient.post<UserPolicyItemResponse>(
    `/policies/${policyId}/applications`,
    {
      application_date: applicationDate,
      application_status: 'SUBMITTED',
      application_note: null,
    },
  )
  return response.data
}

export async function listMyPolicies(params?: {
  tab?: MyPoliciesTab
  sort?: 'recommendation' | 'latest' | 'deadline'
}): Promise<UserPolicyItemResponse[]> {
  const response = await apiClient.get<UserPolicyItemResponse[]>('/users/me/policies', {
    params,
  })
  return response.data
}

export async function deletePolicyProgress(stateId: number): Promise<void> {
  await apiClient.delete(`/users/me/policies/${stateId}/progress`)
}
