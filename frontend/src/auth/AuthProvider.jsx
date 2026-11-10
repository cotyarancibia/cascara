import { useCallback, useState } from 'react'
import { AuthContext } from './AuthContext.js'

// Simulación educativa: estas credenciales en memoria no son seguras.
const initialUsers = [{ firstName: 'Cliente', lastName: 'Demo', email: 'cliente@cascara.test', phone: '', password: 'Campo123!' }]
const normalizeEmail = (email) => email.trim().toLowerCase()

export function AuthProvider({ children }) {
  const [users, setUsers] = useState(initialUsers)
  const [user, setUser] = useState(null)
  const [registrationNotice, setRegistrationNotice] = useState(false)
  const clearRegistrationNotice = useCallback(() => setRegistrationNotice(false), [])

  function login(email, password) {
    const match = users.find((item) => item.email === normalizeEmail(email) && item.password === password)
    if (!match) return false
    setUser({ firstName: match.firstName, lastName: match.lastName, email: match.email, phone: match.phone })
    return true
  }

  function register(newUser) {
    const email = normalizeEmail(newUser.email)
    if (users.some((item) => item.email === email)) return false
    setUsers((current) => [...current, { ...newUser, email }])
    setRegistrationNotice(true)
    return true
  }

  function logout() { setUser(null) }

  return <AuthContext.Provider value={{ user, login, register, logout, registrationNotice, clearRegistrationNotice }}>{children}</AuthContext.Provider>
}
