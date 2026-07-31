import { useEffect, useMemo, useState } from 'react'
import type { PropsWithChildren } from 'react'
import { login as apiLogin, signup as apiSignup } from '../api/auth'
import { clearToken, getToken, setToken as persistToken } from '../api/client'
import { getCurrentUser, getMyProfile, updateDisplayName as apiUpdateDisplayName, updateMyProfile } from '../api/users'
import type { NotificationSettings } from '../types'
import type { SignupRequest, UserProfileResponse, UserProfileUpdate, UserResponse } from '../types/api'
import { AppContext } from './context'

export function AppProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState<string | null>(() => getToken())
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null)
  const [profile, setProfile] = useState<UserProfileResponse | null>(null)
  const [avatarUrl, setAvatarUrl] = useState<string | undefined>(
    () => localStorage.getItem('joopjoop-profile-avatar') || undefined,
  )
  const isLoggedIn = token !== null
  const [notificationSettings, setNotificationSettings] = useState<NotificationSettings>({
    enabled: true,
    sevenDaysBefore: true,
    threeDaysBefore: true,
    deadlineDay: true,
  })
  const [accountId] = useState('nara@example.com')

  useEffect(() => {
    if (!token) return
    let cancelled = false
    Promise.all([getCurrentUser(), getMyProfile()])
      .then(([user, userProfile]) => {
        if (cancelled) return
        setCurrentUser(user)
        setProfile(userProfile)
      })
      .catch(() => {
        if (!cancelled) {
          clearToken()
          setToken(null)
          setCurrentUser(null)
          setProfile(null)
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
    setProfile(null)
  }

  async function refreshProfile() {
    setProfile(await getMyProfile())
  }

  async function updateProfile(payload: UserProfileUpdate) {
    setProfile(await updateMyProfile(payload))
  }

  async function updateDisplayName(nickname: string) {
    setCurrentUser(await apiUpdateDisplayName(nickname))
  }

  function updateAvatarUrl(next: string | undefined) {
    if (next) localStorage.setItem('joopjoop-profile-avatar', next)
    else localStorage.removeItem('joopjoop-profile-avatar')
    setAvatarUrl(next)
  }

  const value = useMemo(
    () => ({
      isLoggedIn,
      token,
      currentUser,
      login,
      signup,
      logout,
      profile,
      refreshProfile,
      updateProfile,
      updateDisplayName,
      avatarUrl,
      updateAvatarUrl,
      notificationSettings,
      updateNotificationSettings: setNotificationSettings,
      accountId,
    }),
    [isLoggedIn, token, currentUser, profile, avatarUrl, notificationSettings, accountId],
  )

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}
