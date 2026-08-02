import type { SignupRequest, UserProfileResponse, UserProfileUpdate, UserResponse } from './api'

export interface AppContextValue {
  isLoggedIn: boolean
  token: string | null
  hasExplicitlyLoggedOut: boolean
  currentUser: UserResponse | null
  login: (email: string, password: string) => Promise<void>
  signup: (payload: SignupRequest) => Promise<void>
  logout: () => void
  profile: UserProfileResponse | null
  refreshProfile: () => Promise<void>
  updateProfile: (payload: UserProfileUpdate) => Promise<void>
  updateDisplayName: (nickname: string) => Promise<void>
  avatarUrl?: string
  updateAvatarUrl: (avatarUrl: string | undefined) => void
  accountId: string
}

export interface ClassNameProps {
  className?: string
}
