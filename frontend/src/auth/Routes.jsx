import { Link, Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './useAuth.js'
import { canAccess } from './permissions.js'

export function ProtectedRoute({ roles }) {
  const { user, initializing } = useAuth()
  if (initializing) return <main className="auth-page"><p className="container-fluid" role="status">Comprobando sesión...</p></main>
  if (!user) return <Navigate to="/login" replace />
  if (!canAccess(user, roles)) return <main className="auth-page"><div className="container-fluid"><h1>ACCESO DENEGADO</h1><p>No tenés permiso para acceder a esta sección.</p><Link to="/">Volver al inicio</Link></div></main>
  return <Outlet />
}

export function GuestRoute() {
  const { user, initializing } = useAuth()
  if (initializing) return <main className="auth-page"><p className="container-fluid" role="status">Comprobando sesión...</p></main>
  return user ? <Navigate to="/" replace /> : <Outlet />
}
