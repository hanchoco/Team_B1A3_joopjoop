import { apiClient } from './client'
import type {
  PolicyBookmarkResponse,
  PolicyDetailResponse,
  PolicyListResponse,
  PolicyMatchDetailResponse,
} from '../types/api'

export interface ListPoliciesParams {
  category_code?: string
  eligibility_status?: 'ELIGIBLE' | 'NEEDS_REVIEW'
  sort?: 'recommendation' | 'latest' | 'deadline'
  page?: number
  size?: number
  keyword?: string
}

export async function listPolicies(params: ListPoliciesParams): Promise<PolicyListResponse> {
  const response = await apiClient.get<PolicyListResponse>('/policies', { params })
  return response.data
}

export async function getPolicy(id: number): Promise<PolicyDetailResponse> {
  const response = await apiClient.get<PolicyDetailResponse>(`/policies/${id}`)
  return response.data
}

export async function getPolicyMatch(id: number): Promise<PolicyMatchDetailResponse> {
  const response = await apiClient.get<PolicyMatchDetailResponse>(`/policies/${id}/match`)
  return response.data
}

export async function bookmarkPolicy(id: number): Promise<PolicyBookmarkResponse> {
  const response = await apiClient.post<PolicyBookmarkResponse>(`/policies/${id}/bookmark`)
  return response.data
}

export async function removeBookmark(id: number): Promise<void> {
  await apiClient.delete(`/policies/${id}/bookmark`)
}
