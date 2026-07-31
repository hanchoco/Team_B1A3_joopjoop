import axios from 'axios'
import type { AxiosRequestConfig } from 'axios'

const TOKEN_STORAGE_KEY = 'joopjoop-access-token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
})

apiClient.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/** Routes where a 401 means "the credential you just typed was wrong", not
 * "your session expired" — these must not trigger a forced /login redirect,
 * so the caller's catch block can show extractErrorMessage() inline instead. */
const AUTH_REDIRECT_EXEMPT: { method: string; url: string }[] = [
  { method: 'post', url: '/auth/login' },
  { method: 'post', url: '/users/me/verify-password' },
  { method: 'patch', url: '/users/me/account' },
  { method: 'delete', url: '/users/me' },
]

function isAuthRedirectExempt(config: AxiosRequestConfig | undefined): boolean {
  if (!config) return false
  const method = (config.method ?? '').toLowerCase()
  const url = config.url ?? ''
  return AUTH_REDIRECT_EXEMPT.some((rule) => rule.method === method && url === rule.url)
}

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (
      axios.isAxiosError(error) &&
      error.response?.status === 401 &&
      !isAuthRedirectExempt(error.config)
    ) {
      clearToken()
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

/** Normalize both the domain-error envelope ({code, detail}) and pydantic's
 * 422 shape ({detail: [{msg, ...}]}) into one human-readable string. */
export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data: unknown = error.response?.data
    if (data && typeof data === 'object') {
      const detail = (data as { detail?: unknown }).detail
      if (typeof detail === 'string') {
        return detail
      }
      if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0] as { msg?: unknown }
        if (typeof first.msg === 'string') {
          return first.msg
        }
      }
    }
    if (error.message) {
      return error.message
    }
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return '알 수 없는 오류가 발생했습니다.'
}
