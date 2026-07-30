import { apiClient } from './client'
import type { UserResponse } from '../types/api'

export async function getCurrentUser(): Promise<UserResponse> {
  const response = await apiClient.get<UserResponse>('/users/me')
  return response.data
}
