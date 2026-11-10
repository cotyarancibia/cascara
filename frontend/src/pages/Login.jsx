import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth.js'
import AuthLayout from './AuthLayout.jsx'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const { login, registrationNotice, clearRegistrationNotice } = useAuth()
  const [registered] = useState(registrationNotice)
  const navigate = useNavigate()

  useEffect(() => { clearRegistrationNotice() }, [clearRegistrationNotice])

  function submit(event) {
    event.preventDefault()
    const missing = [...(!email.trim() ? ['email'] : []), ...(!password ? ['password'] : [])]
    if (missing.length) { setError({ message: 'Completá el correo electrónico y la contraseña.', fields: missing }); return }
    if (!login(email, password)) { setError({ message: 'El correo electrónico o la contraseña son incorrectos.', fields: ['email', 'password'] }); return }
    navigate('/', { replace: true })
  }

  return <AuthLayout title="HOLA DE NUEVO" intro="Qué bueno tenerte por acá. Iniciá sesión para entrar a Cáscara.">
    {registered && <p className="auth-success" role="status">Tu cuenta fue creada. Ya podés iniciar sesión.</p>}
    <form onSubmit={submit} noValidate>
      <div className="mb-3"><label className="form-label" htmlFor="login-email">Correo electrónico</label><input className="form-control" id="login-email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} aria-invalid={error?.fields.includes('email') || undefined} aria-describedby={error?.fields.includes('email') ? 'login-error' : undefined} required /></div>
      <div className="mb-3"><label className="form-label" htmlFor="login-password">Contraseña</label><input className="form-control" id="login-password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} aria-invalid={error?.fields.includes('password') || undefined} aria-describedby={error?.fields.includes('password') ? 'login-error' : undefined} required /></div>
      {error && <p id="login-error" className="auth-error" role="alert">{error.message}</p>}
      <button className="auth-submit" type="submit">INICIAR SESIÓN <span aria-hidden="true">→</span></button>
    </form>
    <p className="auth-switch">¿Todavía no tenés cuenta? <Link to="/register">Registrate</Link></p>
  </AuthLayout>
}
