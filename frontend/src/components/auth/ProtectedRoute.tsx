import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/lib/auth-store'

export function ProtectedRoute() {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <Outlet />
}

export function PublicOnlyRoute() {
  const token = useAuthStore((s) => s.token)
  if (token) return <Navigate to="/" replace />
  return <Outlet />
}
