import { useCallback, useEffect, useRef, useState } from 'react'
import { SESSION_KEY, loginSession, logoutSession, nextValidationDelay, registerUser, restoreSession } from '../api/session.js'
import { AuthContext } from './AuthContext.js'

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null)
  const [initializing, setInitializing] = useState(true)
  const [warning, setWarning] = useState('')
  const [registrationNotice, setRegistrationNotice] = useState(false)
  const operation = useRef(0)
  const clearRegistrationNotice = useCallback(() => setRegistrationNotice(false), [])

  useEffect(() => {
    let active = true
    const validate = (force = false) => {
      const current = ++operation.current
      if (force) { setSession(null); setInitializing(true) }
      restoreSession({ force }).then((result) => {
        if (active && operation.current === current) { setSession(result); setWarning('') }
      }).catch((error) => {
        if (active && operation.current === current) { setSession(null); setWarning(error.message || 'No se pudo comprobar la sesión.') }
      }).finally(() => {
        if (active && operation.current === current) setInitializing(false)
      })
    }
    const onStorage = (event) => { if (event.key === SESSION_KEY || event.key === null) validate(true) }
    window.addEventListener('storage', onStorage)
    validate()
    return () => { active = false; window.removeEventListener('storage', onStorage) }
  }, [])

  useEffect(() => {
    if (!session) return undefined
    let active = true
    const current = operation.current
    const timer = window.setTimeout(() => {
      restoreSession().then((result) => {
        if (active && operation.current === current) setSession(result)
      }).catch((error) => {
        if (active && operation.current === current) { setSession(null); setWarning(error.message || 'No se pudo comprobar la sesión.') }
      })
    }, nextValidationDelay())
    return () => { active = false; window.clearTimeout(timer) }
  }, [session])

  async function login(username, password) {
    const current = ++operation.current
    setWarning('')
    const result = await loginSession(username, password)
    if (current !== operation.current) throw new Error('La sesión cambió en otra pestaña. Intentá nuevamente.')
    setSession(result)
  }

  async function register(data) {
    await registerUser(data)
    setRegistrationNotice(true)
  }

  async function logout() {
    const current = ++operation.current
    const sessionId = session?.sessionId
    setSession(null)
    setWarning('')
    try {
      const result = await logoutSession(sessionId)
      if (!result.revoked && !result.superseded && current === operation.current) setWarning('Se cerró la sesión en este dispositivo, pero no se pudo confirmar la revocación en el servidor.')
    } catch (error) {
      if (current === operation.current) setWarning(`No se pudo confirmar el cierre de sesión en el servidor. ${error.message || 'Revisá el almacenamiento del navegador.'}`)
    }
  }

  return <AuthContext.Provider value={{ user: session?.user || null, initializing, login, register, logout, warning, registrationNotice, clearRegistrationNotice }}>{children}</AuthContext.Provider>
}
