// Backend DTOs (see backend/app/schemas/user.py). Only the auth-flow subset
// needed for now — more are added as later features get wired up.

export type AccountStatus = 'ACTIVE' | 'SUSPENDED' | 'WITHDRAWN'

export interface UserResponse {
  id: number
  email: string
  nickname: string | null
  account_status: AccountStatus
  last_login_at: string | null
  created_at: string
  updated_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserResponse
}

export type ConsentType =
  | 'TERMS_REQUIRED'
  | 'PRIVACY_REQUIRED'
  | 'MARKETING_OPTIONAL'
  | 'THIRD_PARTY_OPTIONAL'

export interface ConsentCreate {
  consent_type: ConsentType
  consent_version: string
  is_agreed: boolean
}

export interface SignupRequest {
  email: string
  password: string
  nickname?: string
  consents?: ConsentCreate[]
}

export interface LoginRequest {
  email: string
  password: string
}

export interface ApiErrorBody {
  code: string
  detail: string
}
