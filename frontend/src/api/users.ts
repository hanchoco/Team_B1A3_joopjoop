import { apiClient } from './client'
import type { UserProfileResponse, UserProfileUpdate, UserResponse } from '../types/api'

export async function getCurrentUser(): Promise<UserResponse> {
  const response = await apiClient.get<UserResponse>('/users/me')
  return response.data
}

export async function getMyProfile(): Promise<UserProfileResponse> {
  const response = await apiClient.get<UserProfileResponse>('/users/me/profile')
  return response.data
}

export async function updateMyProfile(
  payload: UserProfileUpdate,
): Promise<UserProfileResponse> {
  const response = await apiClient.patch<UserProfileResponse>('/users/me/profile', payload)
  return response.data
}

export async function changePassword(payload: {
  current_password: string
  new_password: string
  new_password_confirm: string
}): Promise<UserResponse> {
  const response = await apiClient.patch<UserResponse>('/users/me/account', payload)
  return response.data
}
