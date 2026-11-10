import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './useAuth.js'

export function ProtectedRoute() {
  const { user, initializing } = useAuth()
  if (initializing) return <main className="auth-page"><p className="container-fluid" role="status">Comprobando sesión...</p></main>
  return user ? <Outlet /> : <Navigate to="/login" replace />
}

export function GuestRoute() {
  const { user, initializing } = useAuth()
  if (initializing) return <main className="auth-page"><p className="container-fluid" role="status">Comprobando sesión...</p></main>
  return user ? <Navigate to="/" replace /> : <Outlet />
}
