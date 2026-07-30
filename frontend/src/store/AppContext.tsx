import { useEffect, useMemo, useState } from 'react'
import type { PropsWithChildren } from 'react'
import { login as apiLogin, signup as apiSignup } from '../api/auth'
import { clearToken, getToken, setToken as persistToken } from '../api/client'
import { getCurrentUser } from '../api/users'
import type {
  FavoritePolicy,
  NotificationSettings,
  PreparedPolicy,
  UserProfile,
  UserProfileUpdate,
} from '../types'
import type { SignupRequest, UserResponse } from '../types/api'
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
  const [token, setToken] = useState<string | null>(() => getToken())
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null)
  const isLoggedIn = token !== null
  // TODO(다음 라운드): userProfile 이하는 아직 mock 기반. 실제 프로필 스키마로 교체 예정.
  const [userProfile, setUserProfile] = useState(initialProfile)
  const [preparedPolicies, setPreparedPolicies] = useState<Record<string, PreparedPolicy>>({})
  const [favoritePolicies, setFavoritePolicies] = useState<Record<string, FavoritePolicy>>({
    'youth-rent': {
      id: 'youth-rent',
      title: '청년 월세 한시 특별지원',
      category: '주거',
      deadline: 23,
    },
    'youth-account': { id: 'youth-account', title: '청년도약계좌', category: '금융', deadline: 51 },
  })
  const [notificationSettings, setNotificationSettings] = useState<NotificationSettings>({
    enabled: true,
    sevenDaysBefore: true,
    threeDaysBefore: true,
    deadlineDay: true,
  })
  const [accountId, setAccountId] = useState('nara@example.com')
  const [optionalPrivacyConsent, setOptionalPrivacyConsent] = useState(true)

  useEffect(() => {
    if (!token) return
    let cancelled = false
    getCurrentUser()
      .then((user) => {
        if (!cancelled) setCurrentUser(user)
      })
      .catch(() => {
        if (!cancelled) {
          clearToken()
          setToken(null)
          setCurrentUser(null)
        }
      })
    return () => {
      cancelled = true
    }
  }, [token])

  async function login(email: string, password: string) {
    const result = await apiLogin({ email, password })
    persistToken(result.access_token)
    setToken(result.access_token)
    setCurrentUser(result.user)
  }

  async function signup(payload: SignupRequest) {
    const result = await apiSignup(payload)
    persistToken(result.access_token)
    setToken(result.access_token)
    setCurrentUser(result.user)
  }

  function logout() {
    clearToken()
    setToken(null)
    setCurrentUser(null)
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

  function removePreparation(policyId: string) {
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

  const value = useMemo(
    () => ({
      isLoggedIn,
      token,
      currentUser,
      login,
      signup,
      logout,
      userProfile,
      updateUserProfile,
      preparedPolicies,
      updatePreparation,
      removePreparation,
      favoritePolicies,
      toggleFavorite,
      notificationSettings,
      updateNotificationSettings: setNotificationSettings,
      accountId,
      updateAccountId: setAccountId,
      optionalPrivacyConsent,
      updateOptionalPrivacyConsent: setOptionalPrivacyConsent,
    }),
    [
      isLoggedIn,
      token,
      currentUser,
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
