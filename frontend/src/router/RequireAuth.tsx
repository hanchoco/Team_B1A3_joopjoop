import { Navigate } from 'react-router-dom'
import type { PropsWithChildren } from 'react'
import { useApp } from '../store/useApp'

export default function RequireAuth({ children }: PropsWithChildren) {
  const { token } = useApp()
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return children
}
