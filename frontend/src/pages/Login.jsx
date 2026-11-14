import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth.js'
import AuthLayout from './AuthLayout.jsx'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [pending, setPending] = useState(false)
  const { login, warning, registrationNotice, clearRegistrationNotice } = useAuth()
  const [registered] = useState(registrationNotice)
  const navigate = useNavigate()

  useEffect(() => { clearRegistrationNotice() }, [clearRegistrationNotice])

  async function submit(event) {
    event.preventDefault()
    if (pending) return
    const missing = [...(!username.trim() ? ['username'] : []), ...(!password ? ['password'] : [])]
    if (missing.length) { setError({ message: 'Completá el nombre de usuario y la contraseña.', fields: missing }); return }
    setPending(true)
    setError(null)
    try {
      await login(username.trim(), password)
      navigate('/', { replace: true })
    } catch (error) {
      setError(error.status === 429 ? { message: 'Demasiados intentos. Esperá unos minutos antes de volver a intentar.', fields: [] } : error.status === 401 ? { message: 'El usuario o la contraseña son incorrectos.', fields: ['username', 'password'] } : { message: error.status === 0 || !error.status ? error.message : 'No se pudo conectar o validar la sesión. Intentá nuevamente.', fields: [] })
    } finally { setPending(false) }
  }

  return <AuthLayout title="HOLA DE NUEVO" intro="Qué bueno tenerte por acá. Iniciá sesión para entrar a Cáscara.">
    {registered && <p className="auth-success" role="status">Tu cuenta fue creada. Ya podés iniciar sesión.</p>}
    {warning && <p className="auth-error" role="alert">{warning}</p>}
    <form onSubmit={submit} noValidate>
      <div className="mb-3"><label className="form-label" htmlFor="login-username">Nombre de usuario</label><input className="form-control" id="login-username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} aria-invalid={error?.fields.includes('username') || undefined} aria-describedby={error?.fields.includes('username') ? 'login-error' : undefined} required /></div>
      <div className="mb-3"><label className="form-label" htmlFor="login-password">Contraseña</label><input className="form-control" id="login-password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} aria-invalid={error?.fields.includes('password') || undefined} aria-describedby={error?.fields.includes('password') ? 'login-error' : undefined} required /></div>
      {error && <p id="login-error" className="auth-error" role="alert">{error.message}</p>}
      <button className="auth-submit" type="submit" disabled={pending}>{pending ? 'INGRESANDO...' : 'INICIAR SESIÓN'} <span aria-hidden="true">→</span></button>
    </form>
    <p className="auth-switch">¿Todavía no tenés cuenta? <Link to="/register">Registrate</Link></p>
  </AuthLayout>
}
