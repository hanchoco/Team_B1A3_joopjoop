import axios from 'axios'

export const ACCESS_TOKEN_STORAGE_KEY = 'access_token'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  const accessToken = localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)

  if (accessToken) {
    config.headers.set('Authorization', `Bearer ${accessToken}`)
  }

  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      const requestUrl = error.config?.url ?? ''
      const isAuthenticationRequest =
        requestUrl.includes('/auth/login') || requestUrl.includes('/auth/signup')
      if (!isAuthenticationRequest) {
        localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
        if (window.location.pathname !== '/login') window.location.assign('/login')
      }
    }
    return Promise.reject(error)
  },
)

export default apiClient
