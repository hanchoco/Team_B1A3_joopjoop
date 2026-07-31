import type { SignupRequest, UserProfileResponse, UserProfileUpdate, UserResponse } from './api'

export interface NotificationSettings {
  enabled: boolean
  sevenDaysBefore: boolean
  threeDaysBefore: boolean
  deadlineDay: boolean
}

export interface AppContextValue {
  isLoggedIn: boolean
  token: string | null
  currentUser: UserResponse | null
  login: (email: string, password: string) => Promise<void>
  signup: (payload: SignupRequest) => Promise<void>
  logout: () => void
  profile: UserProfileResponse | null
  refreshProfile: () => Promise<void>
  updateProfile: (payload: UserProfileUpdate) => Promise<void>
  avatarUrl?: string
  updateAvatarUrl: (avatarUrl: string | undefined) => void
  notificationSettings: NotificationSettings
  updateNotificationSettings: (settings: NotificationSettings) => void
  accountId: string
}

export interface ClassNameProps {
  className?: string
}
