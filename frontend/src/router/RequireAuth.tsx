import { Navigate, useLocation } from 'react-router-dom'
import type { PropsWithChildren } from 'react'
import { useApp } from '../store/useApp'

export default function RequireAuth({ children }: PropsWithChildren) {
  const { token } = useApp()
  const location = useLocation()
  if (!token) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ returnTo: `${location.pathname}${location.search}` }}
      />
    )
  }
  return children
}
