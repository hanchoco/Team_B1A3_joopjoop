import type { AuthUser } from './auth'
import apiClient from './client'

export type IncomeBandCode =
  | 'BELOW_50'
  | 'BETWEEN_50_75'
  | 'BETWEEN_75_100'
  | 'BETWEEN_100_120'
  | 'BETWEEN_120_150'
  | 'ABOVE_150'
  | 'UNKNOWN'

export type EmploymentStatusCode =
  'EMPLOYED' | 'SELF_EMPLOYED' | 'UNEMPLOYED' | 'JOB_SEEKER' | 'STUDENT' | 'ON_LEAVE' | 'OTHER'

export type HouseholdTypeCode =
  'SINGLE' | 'COUPLE' | 'WITH_PARENTS' | 'SINGLE_PARENT' | 'MULTI_PERSON' | 'OTHER'

export type HousingTypeCode =
  'OWNED' | 'JEONSE' | 'MONTHLY_RENT' | 'PUBLIC_RENTAL' | 'DORMITORY' | 'WITH_FAMILY' | 'OTHER'

export interface UserProfileResponse {
  user_id: number
  birth_year: number | null
  region_code: string | null
  region_sido: string | null
  region_sigungu: string | null
  income_band_code: IncomeBandCode | null
  employment_status_code: EmploymentStatusCode | null
  household_type_code: HouseholdTypeCode | null
  household_size: number | null
  housing_type_code: HousingTypeCode | null
  onboarding_completed: boolean
  created_at: string
  updated_at: string
}

export type UserProfilePatch = Partial<
  Pick<
    UserProfileResponse,
    | 'birth_year'
    | 'region_code'
    | 'region_sido'
    | 'region_sigungu'
    | 'income_band_code'
    | 'employment_status_code'
    | 'household_type_code'
    | 'household_size'
    | 'housing_type_code'
    | 'onboarding_completed'
  >
>

export async function getCurrentUser(): Promise<AuthUser> {
  const { data } = await apiClient.get<AuthUser>('/api/v1/users/me')
  return data
}

export async function getCurrentUserProfile(): Promise<UserProfileResponse> {
  const { data } = await apiClient.get<UserProfileResponse>('/api/v1/users/me/profile')
  return data
}

export async function updateCurrentUserProfile(
  payload: UserProfilePatch,
): Promise<UserProfileResponse> {
  const { data } = await apiClient.patch<UserProfileResponse>('/api/v1/users/me/profile', payload)
  return data
}

export interface AccountUpdateRequest {
  current_password: string
  email?: string
  nickname?: string
  new_password?: string
  new_password_confirm?: string
}

export async function verifyCurrentPassword(currentPassword: string): Promise<string> {
  const { data } = await apiClient.post<{ message: string }>('/api/v1/users/me/verify-password', {
    current_password: currentPassword,
  })
  return data.message
}

export async function updateCurrentAccount(payload: AccountUpdateRequest): Promise<AuthUser> {
  const { data } = await apiClient.patch<AuthUser>('/api/v1/users/me/account', payload)
  return data
}

export async function withdrawCurrentAccount(currentPassword: string): Promise<string> {
  const { data } = await apiClient.delete<{ message: string }>('/api/v1/users/me', {
    data: {
      current_password: currentPassword,
      confirm_withdrawal: true,
    },
  })
  return data.message
}
