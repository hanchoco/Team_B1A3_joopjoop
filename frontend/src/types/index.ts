export interface Region {
  city: string
  district: string
}

export interface Housing {
  type: string
  monthlyRent: number
}

export interface UserProfile {
  id: string
  name: string
  age: number
  region: Region
  housing: Housing
  annualIncome: number
  regionName: string
  monthlyIncome: number
  employment: string
  housingType: string
  concern: string
}

export type UserProfileUpdate = Partial<
  Pick<
    UserProfile,
    'age' | 'regionName' | 'monthlyIncome' | 'employment' | 'housingType' | 'concern'
  >
>

export interface FavoritePolicy {
  id: string
  title: string
  category: string
  deadline: number
}

export interface PreparedPolicy {
  id: string
  title: string
  progress: number
  completed: number
  total: number
  completedIds?: number[]
  status?: 'preparing'
  deadline?: number
}

export interface NotificationSettings {
  enabled: boolean
  sevenDaysBefore: boolean
  threeDaysBefore: boolean
  deadlineDay: boolean
}

export interface AppContextValue {
  isLoggedIn: boolean
  login: () => void
  logout: () => void
  userProfile: UserProfile
  updateUserProfile: (profile: UserProfileUpdate) => void
  preparedPolicies: Record<string, PreparedPolicy>
  updatePreparation: (policy: PreparedPolicy) => void
  removePreparation: (policyId: string) => void
  favoritePolicies: Record<string, FavoritePolicy>
  toggleFavorite: (policy: FavoritePolicy) => void
  notificationSettings: NotificationSettings
  updateNotificationSettings: (settings: NotificationSettings) => void
  accountId: string
  updateAccountId: (accountId: string) => void
  optionalPrivacyConsent: boolean
  updateOptionalPrivacyConsent: (consented: boolean) => void
}

export interface ClassNameProps {
  className?: string
}
