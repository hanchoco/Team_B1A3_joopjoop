import { apiClient } from './client'
import type { LoginRequest, SignupRequest, TokenResponse } from '../types/api'

export async function signup(payload: SignupRequest): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/auth/signup', payload)
  return response.data
}

export async function login(payload: LoginRequest): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/auth/login', payload)
  return response.data
}
