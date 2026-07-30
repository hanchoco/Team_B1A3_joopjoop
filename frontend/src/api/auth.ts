import axios from 'axios'
import apiClient, { ACCESS_TOKEN_STORAGE_KEY } from './client'

export interface LoginRequest {
  email: string
  password: string
}

export interface ConsentRequest {
  consent_type: string
  consent_version: string
  is_agreed: boolean
}

export interface SignupRequest {
  email: string
  password: string
  nickname?: string
  consents?: ConsentRequest[]
}

export interface AuthUser {
  id: number
  email: string
  nickname: string | null
  account_status: string
  last_login_at: string | null
  created_at: string
  updated_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

interface ApiErrorResponse {
  detail?: string
}

export function getAuthErrorMessage(error: unknown, fallbackMessage: string): string {
  if (!axios.isAxiosError<ApiErrorResponse>(error)) return fallbackMessage
  return typeof error.response?.data?.detail === 'string'
    ? error.response.data.detail
    : fallbackMessage
}

function saveAccessToken(response: AuthResponse): AuthResponse {
  localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, response.access_token)
  return response
}

export function clearAccessToken(): void {
  localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
}

export async function login(payload: LoginRequest): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/api/v1/auth/login', payload)
  return saveAccessToken(data)
}

export async function signup(payload: SignupRequest): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/api/v1/auth/signup', payload)
  return saveAccessToken(data)
}
