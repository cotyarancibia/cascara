import { ApiError, request } from './http.js'

export const SESSION_KEY = 'cascara_session'
const LEGACY_KEYS = ['cascara_access', 'cascara_refresh']
const LOCK_NAME = 'cascara-session'
const validToken = (value) => typeof value === 'string' && value.trim().length > 0
const storageError = () => new ApiError(0, null, 'No se puede acceder al almacenamiento del navegador. Revisá su configuración para iniciar sesión.')
const changedError = () => new ApiError(0, null, 'La sesión cambió en otra pestaña. Intentá nuevamente.')

export function createSessionService({ storage = () => globalThis.localStorage, locks = () => globalThis.navigator?.locks, http = request, lockTimeoutMs = 35000, makeId = () => globalThis.crypto.randomUUID() } = {}) {
  let restoration = null

  function read() {
    try {
      const raw = storage().getItem(SESSION_KEY)
      if (!raw) return null
      const value = JSON.parse(raw)
      if (typeof value.id !== 'string' || !validToken(value.access) || !validToken(value.refresh)) throw new ApiError(0, null, 'La sesión guardada no es válida.')
      return value
    } catch (error) {
      if (error instanceof ApiError) throw error
      if (error instanceof SyntaxError) throw new ApiError(0, null, 'La sesión guardada no es válida.')
      throw storageError()
    }
  }

  function write(value) {
    try { storage().setItem(SESSION_KEY, JSON.stringify(value)) } catch { throw storageError() }
  }

  function remove() {
    try { storage().removeItem(SESSION_KEY) } catch { throw storageError() }
  }

  function migrateLegacy() {
    let access, refresh
    try { access = storage().getItem(LEGACY_KEYS[0]); refresh = storage().getItem(LEGACY_KEYS[1]) } catch { throw storageError() }
    if (validToken(access) && validToken(refresh)) {
      write({ id: makeId(), access, refresh })
    }
    try { LEGACY_KEYS.forEach((key) => storage().removeItem(key)) } catch { throw storageError() }
  }

  async function exclusive(callback) {
    const manager = locks()
    if (!manager?.request) throw new ApiError(0, null, 'El navegador no permite coordinar la sesión entre pestañas. Usá un navegador compatible con Web Locks.')
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), lockTimeoutMs)
    try {
      return await manager.request(LOCK_NAME, { mode: 'exclusive', signal: controller.signal }, async () => {
        clearTimeout(timer)
        return callback()
      })
    } catch (error) {
      if (controller.signal.aborted) throw new ApiError(0, null, 'La coordinación de sesión agotó el tiempo de espera. Intentá nuevamente.')
      throw error
    } finally { clearTimeout(timer) }
  }

  function ensurePair(pair) {
    if (!validToken(pair?.access) || !validToken(pair?.refresh)) throw new ApiError(0, null, 'La respuesta de renovación o inicio de sesión está incompleta.')
    return pair
  }

  async function getProfile(access) {
    const user = await http('/auth/profile/', { access })
    if (!user || !Number.isInteger(user.id) || typeof user.username !== 'string') throw new ApiError(0, null, 'La respuesta del perfil no es válida.')
    return user
  }

  async function validateLocked(session) {
    let active = session
    try {
      let user
      try { user = await getProfile(active.access) }
      catch (error) {
        if (error.status !== 401) throw error
        const next = ensurePair(await http('/auth/refresh/', { method: 'POST', body: { refresh: active.refresh } }))
        const current = read()
        if (current?.id !== active.id || current.refresh !== active.refresh) throw changedError()
        active = { id: active.id, access: next.access, refresh: next.refresh }
        write(active)
        user = await getProfile(active.access)
      }
      if (read()?.id !== active.id) throw changedError()
      return { user, sessionId: active.id }
    } catch (error) {
      const current = read()
      if (current?.id === active.id && current.refresh === active.refresh) remove()
      if (error.status === 401) return null
      throw error
    }
  }

  function restoreSession({ force = false } = {}) {
    if (restoration && !force) return restoration
    const pending = exclusive(async () => {
      let current = read()
      if (!current) { migrateLegacy(); current = read() }
      return current ? validateLocked(current) : null
    })
    restoration = pending
    pending.then(() => { if (restoration === pending) restoration = null }, () => { if (restoration === pending) restoration = null })
    return pending
  }

  async function loginSession(username, password) {
    const expected = read()?.id || null
    const pair = ensurePair(await http('/auth/login/', { method: 'POST', body: { username, password } }))
    return exclusive(async () => {
      if ((read()?.id || null) !== expected) throw changedError()
      const user = await getProfile(pair.access)
      if ((read()?.id || null) !== expected) throw changedError()
      const session = { id: makeId(), access: pair.access, refresh: pair.refresh }
      write(session)
      return { user, sessionId: session.id }
    })
  }

  async function logoutSession(expectedId) {
    try { return await exclusive(async () => {
      const current = read()
      if (!current || current.id !== expectedId) return { revoked: false, superseded: true }
      remove()
      try {
        await http('/auth/logout/', { method: 'POST', access: current.access, body: { refresh: current.refresh } })
        return { revoked: true }
      } catch (error) {
        if (error.status !== 401) return { revoked: false }
        try {
          const next = ensurePair(await http('/auth/refresh/', { method: 'POST', body: { refresh: current.refresh } }))
          await http('/auth/logout/', { method: 'POST', access: next.access, body: { refresh: next.refresh } })
          return { revoked: true }
        } catch { return { revoked: false } }
      }
    }) } catch (error) {
      // If the lock wait times out, remove only the session this logout owns.
      // Any pending refresh checks the stored identity again before writing.
      if (read()?.id === expectedId) remove()
      throw error
    }
  }

  function nextValidationDelay() {
    try {
      const payload = read().access.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
      const expiry = JSON.parse(atob(payload)).exp
      if (typeof expiry !== 'number' || !Number.isFinite(expiry)) return 60000
      return Math.max(1000, Math.min(2147483647, expiry * 1000 - Date.now() + 1000))
    } catch { return 60000 }
  }

  return { restoreSession, loginSession, logoutSession, nextValidationDelay }
}

const session = createSessionService()
export const { restoreSession, loginSession, logoutSession, nextValidationDelay } = session
export function registerUser(data) { return request('/auth/register/', { method: 'POST', body: data }) }
