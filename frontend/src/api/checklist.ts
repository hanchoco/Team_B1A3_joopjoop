import { apiClient } from './client'
import type {
  ChecklistResponse,
  ConditionConfirmationUpdate,
  DocumentProgressUpdate,
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
