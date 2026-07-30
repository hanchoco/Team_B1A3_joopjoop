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
  birthYear: number
  incomeBracket: string
  householdType: string
  avatarUrl?: string
}

export type UserProfileUpdate = Partial<
  Pick<
    UserProfile,
    | 'name'
    | 'age'
    | 'regionName'
    | 'monthlyIncome'
    | 'employment'
    | 'housingType'
    | 'concern'
    | 'birthYear'
    | 'incomeBracket'
    | 'householdType'
    | 'avatarUrl'
  >
>

export type EligibilityStatus = 'ELIGIBLE' | 'NEEDS_REVIEW' | 'INELIGIBLE'

export interface Policy {
  id: number
  title: string
  description: string
  category: string
  possibility: EligibilityStatus
  chance: string
  benefit: string
  condition: string
  matchedConditions: number
  totalConditions: number
  deadline: number
  minAge: number
  maxAge: number
  regions: string[]
  incomeLimit: number
  employments: string[]
  housingTypes: string[]
}

export interface FavoritePolicy {
  id: number
  title: string
  category: string
  deadline: number
}

export interface PreparedPolicy {
  id: number
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
  isAuthLoading: boolean
  login: () => void
  logout: () => void
  userProfile: UserProfile
  updateUserProfile: (profile: UserProfileUpdate) => void
  saveUserProfile: (profile: UserProfileUpdate, onboardingCompleted?: boolean) => Promise<void>
  preparedPolicies: Record<number, PreparedPolicy>
  updatePreparation: (policy: PreparedPolicy) => void
  removePreparation: (policyId: number) => void
  favoritePolicies: Record<number, FavoritePolicy>
  toggleFavorite: (policy: FavoritePolicy) => void
  resetPolicyState: () => void
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
