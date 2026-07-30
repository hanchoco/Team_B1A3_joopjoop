import { apiClient } from './client'
import type { PolicyQuestionRequest, PolicyQuestionResponse } from '../types/api'

export async function askPolicyQuestion(
  policyId: number,
  question: string,
): Promise<PolicyQuestionResponse> {
  const payload: PolicyQuestionRequest = { question }
  const response = await apiClient.post<PolicyQuestionResponse>(
    `/policies/${policyId}/questions`,
    payload,
  )
  return response.data
}
