import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth.js'
import AuthLayout from './AuthLayout.jsx'

const fields = [
  { name: 'firstName', label: 'Nombre', autoComplete: 'given-name' },
  { name: 'lastName', label: 'Apellido', autoComplete: 'family-name' },
  { name: 'email', label: 'Correo electrónico', type: 'email', autoComplete: 'email' },
  { name: 'phone', label: 'Teléfono', type: 'tel', autoComplete: 'tel' },
  { name: 'password', label: 'Contraseña', type: 'password', autoComplete: 'new-password' },
  { name: 'confirmation', label: 'Confirmar contraseña', type: 'password', autoComplete: 'new-password' },
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
  const { register } = useAuth()
  const navigate = useNavigate()

  function submit(event) {
    event.preventDefault()
    const missing = Object.keys(form).filter((name) => !form[name].trim())
    if (missing.length) { setError({ message: 'Completá todos los campos.', fields: missing }); return }
    if (!isValidEmail(form.email)) { setError({ message: 'Ingresá un correo electrónico válido.', fields: ['email'] }); return }
    if (form.password !== form.confirmation) { setError({ message: 'Las contraseñas no coinciden.', fields: ['password', 'confirmation'] }); return }
    const { confirmation, ...user } = form
    void confirmation
    if (!register({ ...user, firstName: user.firstName.trim(), lastName: user.lastName.trim(), phone: user.phone.trim() })) { setError({ message: 'Ya existe una cuenta con ese correo electrónico.', fields: ['email'] }); return }
    navigate('/login', { replace: true })
  }

  return <AuthLayout title="SUMATE A CÁSCARA" intro="Creá tu cuenta y llevá un poquito del campo a tu mesa.">
    <form onSubmit={submit} noValidate>
      <div className="row g-3">{fields.map(({ name, label, type = 'text', autoComplete }) => <div className={name === 'email' ? 'col-12' : 'col-sm-6'} key={name}>
        <label className="form-label" htmlFor={`register-${name}`}>{label}</label>
        <input className="form-control" id={`register-${name}`} type={type} autoComplete={autoComplete} value={form[name]} onChange={(event) => setForm({ ...form, [name]: event.target.value })} aria-invalid={error?.fields.includes(name) || undefined} aria-describedby={error?.fields.includes(name) ? 'register-error' : undefined} required />
      </div>)}</div>
      {error && <p id="register-error" className="auth-error" role="alert">{error.message}</p>}
      <button className="auth-submit" type="submit">CREAR CUENTA <span aria-hidden="true">→</span></button>
    </form>
    <p className="auth-switch">¿Ya tenés cuenta? <Link to="/login">Iniciá sesión</Link></p>
  </AuthLayout>
}
