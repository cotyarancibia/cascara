import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth.js'
import AuthLayout from './AuthLayout.jsx'

const fields = [
  { name: 'username', label: 'Nombre de usuario', autoComplete: 'username' },
  { name: 'email', label: 'Correo electrónico', type: 'email', autoComplete: 'email' },
  { name: 'telefono', label: 'Teléfono (opcional)', type: 'tel', autoComplete: 'tel', optional: true },
  { name: 'password', label: 'Contraseña', type: 'password', autoComplete: 'new-password' },
  { name: 'password_confirm', label: 'Confirmar contraseña', type: 'password', autoComplete: 'new-password' },
]
const emptyForm = Object.fromEntries(fields.map(({ name }) => [name, '']))

function isValidEmail(value) {
  const parts = value.trim().split('@')
  if (parts.length !== 2 || !/^[^\s@]+$/.test(parts[0])) return false
  const labels = parts[1].split('.')
  return labels.length >= 2 && labels.every((label) => /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/i.test(label)) && /^[a-z]{2,}$/i.test(labels.at(-1))
}

export default function Register() {
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState(null)
  const [pending, setPending] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  async function submit(event) {
    event.preventDefault()
    if (pending) return
    const missing = fields.filter(({ name, optional }) => !optional && !form[name].trim()).map(({ name }) => name)
    if (missing.length) { setError({ message: 'Completá todos los campos.', fields: missing }); return }
    if (!isValidEmail(form.email)) { setError({ message: 'Ingresá un correo electrónico válido.', fields: ['email'] }); return }
    if (form.password !== form.password_confirm) { setError({ message: 'Las contraseñas no coinciden.', fields: ['password', 'password_confirm'] }); return }
    setPending(true)
    setError(null)
    try {
      await register({ ...form, username: form.username.trim(), email: form.email.trim(), telefono: form.telefono.trim() })
      navigate('/login', { replace: true })
    } catch (error) {
      const data = error.data && typeof error.data === 'object' ? error.data : {}
      const affected = fields.filter(({ name }) => data[name]).map(({ name }) => name)
      const messages = Object.values(data).flatMap((value) => Array.isArray(value) ? value : [value]).filter((value) => typeof value === 'string')
      setError({ message: error.status === 429 ? 'Demasiados intentos de registro. Esperá antes de volver a intentar.' : messages.join(' ') || (error.status === 0 ? error.message : 'No se pudo completar el registro. Intentá nuevamente.'), fields: affected })
    } finally { setPending(false) }
  }

  return <AuthLayout title="SUMATE A CÁSCARA" intro="Creá tu cuenta y llevá un poquito del campo a tu mesa.">
    <form onSubmit={submit} noValidate>
      <div className="row g-3">{fields.map(({ name, label, type = 'text', autoComplete, optional }) => <div className={name === 'email' ? 'col-12' : 'col-sm-6'} key={name}>
        <label className="form-label" htmlFor={`register-${name}`}>{label}</label>
        <input className="form-control" id={`register-${name}`} type={type} autoComplete={autoComplete} value={form[name]} onChange={(event) => setForm({ ...form, [name]: event.target.value })} aria-invalid={error?.fields.includes(name) || undefined} aria-describedby={error?.fields.includes(name) ? 'register-error' : undefined} required={!optional} />
      </div>)}</div>
      {error && <p id="register-error" className="auth-error" role="alert">{error.message}</p>}
      <button className="auth-submit" type="submit" disabled={pending}>{pending ? 'CREANDO CUENTA...' : 'CREAR CUENTA'} <span aria-hidden="true">→</span></button>
    </form>
    <p className="auth-switch">¿Ya tenés cuenta? <Link to="/login">Iniciá sesión</Link></p>
  </AuthLayout>
}
