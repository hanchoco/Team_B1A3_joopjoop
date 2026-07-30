import apiClient from './client'

export interface PolicyQuestionResponse {
  answer: string
  suggested_questions: string[]
}

export async function askPolicyQuestion(
  policyId: number,
  question: string,
): Promise<PolicyQuestionResponse> {
  const { data } = await apiClient.post<PolicyQuestionResponse>(
    `/api/v1/policies/${policyId}/questions`,
    { question },
  )
  return data
}
