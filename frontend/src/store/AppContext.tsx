import { useMemo, useState } from 'react'
import type { PropsWithChildren } from 'react'
import type {
  FavoritePolicy,
  NotificationSettings,
  PreparedPolicy,
  UserProfile,
  UserProfileUpdate,
} from '../types'
import mockData from '../utils/mockData.json'
import { AppContext } from './context'

export function AppProvider({ children }: PropsWithChildren) {
  const savedAvatarUrl = localStorage.getItem('joopjoop-profile-avatar') || undefined
  const initialProfile: UserProfile = {
    ...mockData.userProfile,
    regionName: mockData.userProfile.region.city.replace('특별시', ''),
    monthlyIncome: Math.round(mockData.userProfile.annualIncome / 12 / 10000),
    employment: '구직 중',
    housingType: mockData.userProfile.housing.type,
    concern: '',
    birthYear: new Date().getFullYear() - mockData.userProfile.age,
    incomeBracket: '월 201~300만 원',
    householdType: '1인 가구',
    avatarUrl: savedAvatarUrl,
  }
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [userProfile, setUserProfile] = useState(initialProfile)
  const [preparedPolicies, setPreparedPolicies] = useState<Record<number, PreparedPolicy>>({})
  const [favoritePolicies, setFavoritePolicies] = useState<Record<number, FavoritePolicy>>({})
  const [notificationSettings, setNotificationSettings] = useState<NotificationSettings>({
    enabled: true,
    sevenDaysBefore: true,
    threeDaysBefore: true,
    deadlineDay: true,
  })
  const [accountId, setAccountId] = useState('nara@example.com')
  const [optionalPrivacyConsent, setOptionalPrivacyConsent] = useState(true)

  function login() {
    setIsLoggedIn(true)
  }

  function logout() {
    setIsLoggedIn(false)
  }

  function updateUserProfile(profile: UserProfileUpdate) {
    if ('avatarUrl' in profile) {
      if (profile.avatarUrl) localStorage.setItem('joopjoop-profile-avatar', profile.avatarUrl)
      else localStorage.removeItem('joopjoop-profile-avatar')
    }
    setUserProfile((current) => ({
      ...current,
      ...profile,
      region: {
        ...current.region,
        city: profile.regionName ? `${profile.regionName}특별시` : current.region.city,
      },
      housing: {
        ...current.housing,
        type: profile.housingType || current.housing.type,
      },
      annualIncome: profile.monthlyIncome
        ? Number(profile.monthlyIncome) * 12 * 10000
        : current.annualIncome,
      age: profile.birthYear ? new Date().getFullYear() - profile.birthYear : current.age,
    }))
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

  const value = useMemo(
    () => ({
      isLoggedIn,
      login,
      logout,
      userProfile,
      updateUserProfile,
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
    }),
    [
      isLoggedIn,
      userProfile,
      preparedPolicies,
      favoritePolicies,
      notificationSettings,
      accountId,
      optionalPrivacyConsent,
    ],
  )

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}
