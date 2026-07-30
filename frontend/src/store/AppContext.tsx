import { useCallback, useEffect, useState } from 'react'
import type { PropsWithChildren } from 'react'
import { clearAccessToken } from '../api/auth'
import { ACCESS_TOKEN_STORAGE_KEY } from '../api/client'
import { getCurrentUser, getCurrentUserProfile, updateCurrentUserProfile } from '../api/users'
import type {
  FavoritePolicy,
  NotificationSettings,
  PreparedPolicy,
  UserProfile,
  UserProfileUpdate,
} from '../types'
import { fromUserProfileResponse, toUserProfilePatch } from '../utils/profileMappings'
import { AppContext } from './context'

function createInitialProfile(): UserProfile {
  const savedAvatarUrl = localStorage.getItem('joopjoop-profile-avatar') || undefined
  return {
    id: '',
    name: '사용자',
    age: 0,
    region: { city: '', district: '' },
    housing: { type: '월세', monthlyRent: 0 },
    annualIncome: 0,
    regionName: '',
    monthlyIncome: 0,
    employment: '구직 중',
    housingType: '월세',
    concern: '',
    birthYear: 2000,
    incomeBracket: '월 201~300만 원',
    householdType: '1인 가구',
    avatarUrl: savedAvatarUrl,
  }
}

function mergeLocalProfile(current: UserProfile, profile: UserProfileUpdate): UserProfile {
  return {
    ...current,
    ...profile,
    region: {
      ...current.region,
      city: profile.regionName ?? current.region.city,
    },
    housing: {
      ...current.housing,
      type: profile.housingType ?? current.housing.type,
    },
    annualIncome:
      profile.monthlyIncome !== undefined
        ? Number(profile.monthlyIncome) * 12 * 10000
        : current.annualIncome,
    age:
      profile.birthYear !== undefined ? new Date().getFullYear() - profile.birthYear : current.age,
  }
}

export function AppProvider({ children }: PropsWithChildren) {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [isAuthLoading, setIsAuthLoading] = useState(
    Boolean(localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)),
  )
  const [userProfile, setUserProfile] = useState(createInitialProfile)
  const [preparedPolicies, setPreparedPolicies] = useState<Record<number, PreparedPolicy>>({})
  const [favoritePolicies, setFavoritePolicies] = useState<Record<number, FavoritePolicy>>({})
  const [notificationSettings, setNotificationSettings] = useState<NotificationSettings>({
    enabled: true,
    emailEnabled: true,
    pushEnabled: true,
    sevenDaysBefore: true,
    threeDaysBefore: true,
    deadlineDay: true,
  })
  const [accountId, setAccountId] = useState('')
  const [optionalPrivacyConsent, setOptionalPrivacyConsent] = useState(true)

  const restoreAuthenticatedUser = useCallback(async (): Promise<void> => {
    const [user, profile] = await Promise.all([getCurrentUser(), getCurrentUserProfile()])
    setAccountId(user.email)
    setUserProfile((current) =>
      fromUserProfileResponse(profile, {
        ...current,
        name: user.nickname ?? user.email.split('@')[0],
      }),
    )
    setIsLoggedIn(true)
  }, [])

  useEffect(() => {
    if (!localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)) return
    let isCurrent = true

    Promise.all([getCurrentUser(), getCurrentUserProfile()])
      .then(([user, profile]) => {
        if (!isCurrent) return
        setAccountId(user.email)
        setUserProfile((current) =>
          fromUserProfileResponse(profile, {
            ...current,
            name: user.nickname ?? user.email.split('@')[0],
          }),
        )
        setIsLoggedIn(true)
      })
      .catch(() => {
        if (!isCurrent) return
        clearAccessToken()
        setIsLoggedIn(false)
      })
      .finally(() => {
        if (isCurrent) setIsAuthLoading(false)
      })

    return () => {
      isCurrent = false
    }
  }, [])

  async function login(): Promise<void> {
    await restoreAuthenticatedUser()
  }

  function logout() {
    clearAccessToken()
    setIsLoggedIn(false)
    setUserProfile(createInitialProfile())
    setAccountId('')
    setPreparedPolicies({})
    setFavoritePolicies({})
  }

  function updateUserProfile(profile: UserProfileUpdate) {
    if ('avatarUrl' in profile) {
      if (profile.avatarUrl) localStorage.setItem('joopjoop-profile-avatar', profile.avatarUrl)
      else localStorage.removeItem('joopjoop-profile-avatar')
    }
    setUserProfile((current) => mergeLocalProfile(current, profile))
  }

  async function saveUserProfile(
    profile: UserProfileUpdate,
    onboardingCompleted?: boolean,
  ): Promise<void> {
    const payload = toUserProfilePatch(profile, onboardingCompleted)
    const response = await updateCurrentUserProfile(payload)
    updateUserProfile(profile)
    setUserProfile((current) => fromUserProfileResponse(response, current))
  }

  function updatePreparation(policy: PreparedPolicy) {
    setPreparedPolicies((current) => ({
      ...current,
      [policy.id]: {
        ...current[policy.id],
        ...policy,
        status: 'preparing',
      },
    }))
  }

  function removePreparation(policyId: number) {
    setPreparedPolicies((current) => {
      const next = { ...current }
      delete next[policyId]
      return next
    })
  }

  function toggleFavorite(policy: FavoritePolicy) {
    setFavoritePolicies((current) => {
      if (current[policy.id]) {
        const next = { ...current }
        delete next[policy.id]
        return next
      }
      return { ...current, [policy.id]: policy }
    })
  }

  function resetPolicyState() {
    setPreparedPolicies({})
    setFavoritePolicies({})
  }

  const value = {
    isLoggedIn,
    isAuthLoading,
    login,
    logout,
    userProfile,
    updateUserProfile,
    saveUserProfile,
    preparedPolicies,
    updatePreparation,
    removePreparation,
    favoritePolicies,
    toggleFavorite,
    resetPolicyState,
    notificationSettings,
    updateNotificationSettings: setNotificationSettings,
    accountId,
    updateAccountId: setAccountId,
    optionalPrivacyConsent,
    updateOptionalPrivacyConsent: setOptionalPrivacyConsent,
  }

  if (isAuthLoading) {
    return (
      <div className="grid min-h-screen place-items-center bg-amber-50/50">
        <div className="text-center">
          <span className="mx-auto block h-10 w-10 animate-spin rounded-full border-4 border-amber-200 border-t-amber-500" />
          <p className="mt-4 text-sm font-semibold text-amber-900">
            로그인 정보를 안전하게 확인하고 있어요.
          </p>
        </div>
      </div>
    )
  }

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}
