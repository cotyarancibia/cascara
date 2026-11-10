import test from 'node:test'
import assert from 'node:assert/strict'
import { ApiError, createHttpClient } from '../src/api/http.js'
import { createSessionService, SESSION_KEY } from '../src/api/session.js'

const profile = { id: 1, username: 'cliente', email: 'cliente@example.test', role: 'CLIENTE' }
const pair = { access: 'access-1', refresh: 'refresh-1' }

function setup(http) {
  const values = new Map()
  const storage = { getItem: (key) => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: (key) => values.delete(key) }
  let queue = Promise.resolve()
  const locks = { request: (_name, _options, callback) => { const result = queue.then(callback); queue = result.catch(() => {}); return result } }
  let id = 0
  const create = () => createSessionService({ storage: () => storage, locks: () => locks, http, makeId: () => `session-${++id}` })
  return { values, storage, create }
}

test('login validates the server profile before authenticating', async () => {
  const calls = []
  const env = setup(async (url, options) => { calls.push([url, options]); return url.endsWith('/login/') ? pair : profile })
  const result = await env.create().loginSession('cliente', 'ficticia')
  assert.deepEqual(result.user, profile)
  assert.deepEqual(calls[0][1].body, { username: 'cliente', password: 'ficticia' })
  assert.equal(calls[1][1].access, 'access-1')
})

test('two tabs serialize refresh and reuse the rotated pair', async () => {
  let refreshCalls = 0
  const env = setup(async (url, options) => {
    if (url.endsWith('/refresh/')) { refreshCalls++; return { access: 'access-2', refresh: 'refresh-2' } }
    if (options.access === 'access-1') throw new ApiError(401)
    return profile
  })
  env.storage.setItem(SESSION_KEY, JSON.stringify({ id: 'shared', ...pair }))
  const [a, b] = await Promise.all([env.create().restoreSession(), env.create().restoreSession()])
  assert.equal(a.user.username, 'cliente')
  assert.equal(b.user.username, 'cliente')
  assert.equal(refreshCalls, 1)
  assert.equal(JSON.parse(env.storage.getItem(SESSION_KEY)).refresh, 'refresh-2')
})

test('logout clears the shared session even when revocation fails', async () => {
  const env = setup(async () => { throw new ApiError(0) })
  env.storage.setItem(SESSION_KEY, JSON.stringify({ id: 'shared', ...pair }))
  assert.deepEqual(await env.create().logoutSession('shared'), { revoked: false })
  assert.equal(env.storage.getItem(SESSION_KEY), null)
})

test('an old logout cannot remove or revoke a new account', async () => {
  let calls = 0
  const env = setup(async () => { calls++; return null })
  env.storage.setItem(SESSION_KEY, JSON.stringify({ id: 'new-account', ...pair }))
  assert.deepEqual(await env.create().logoutSession('old-account'), { revoked: false, superseded: true })
  assert.equal(JSON.parse(env.storage.getItem(SESSION_KEY)).id, 'new-account')
  assert.equal(calls, 0)
})

test('incomplete rotated response clears the old session', async () => {
  const env = setup(async (url) => { if (url.endsWith('/refresh/')) return { access: 'new-access' }; throw new ApiError(401) })
  env.storage.setItem(SESSION_KEY, JSON.stringify({ id: 'shared', ...pair }))
  await assert.rejects(env.create().restoreSession(), /incompleta/)
  assert.equal(env.storage.getItem(SESSION_KEY), null)
})

test('unavailable storage reports an error instead of hanging', async () => {
  const env = setup(async () => profile)
  const service = createSessionService({ storage: () => { throw new Error('blocked') }, locks: () => ({ request: (_n, _o, callback) => callback() }) })
  await assert.rejects(service.restoreSession(), /almacenamiento/)
  assert.equal(env.values.size, 0)
})

test('missing Web Locks fails closed', async () => {
  const env = setup(async () => profile)
  const service = createSessionService({ storage: () => env.storage, locks: () => null })
  await assert.rejects(service.restoreSession(), /Web Locks/)
})

test('legacy tokens migrate as one session and validate with the backend', async () => {
  const env = setup(async () => profile)
  env.storage.setItem('cascara_access', pair.access)
  env.storage.setItem('cascara_refresh', pair.refresh)
  const result = await env.create().restoreSession()
  assert.equal(result.user.username, 'cliente')
  assert.equal(JSON.parse(env.storage.getItem(SESSION_KEY)).refresh, pair.refresh)
  assert.equal(env.storage.getItem('cascara_access'), null)
  assert.equal(env.storage.getItem('cascara_refresh'), null)
})

test('an invalid token never authenticates and its session is removed', async () => {
  const env = setup(async () => { throw new ApiError(401) })
  env.storage.setItem(SESSION_KEY, JSON.stringify({ id: 'bad', ...pair }))
  assert.equal(await env.create().restoreSession(), null)
  assert.equal(env.storage.getItem(SESSION_KEY), null)
})

test('a late refresh cannot restore a session removed while waiting', async () => {
  let release, started
  const begin = new Promise((resolve) => { started = resolve })
  const deferred = new Promise((resolve) => { release = resolve })
  const env = setup(async (url) => {
    if (url.endsWith('/refresh/')) { started(); return deferred }
    throw new ApiError(401)
  })
  env.storage.setItem(SESSION_KEY, JSON.stringify({ id: 'shared', ...pair }))
  const restoring = env.create().restoreSession()
  await begin
  env.storage.removeItem(SESSION_KEY)
  release({ access: 'rotated-access', refresh: 'rotated-refresh' })
  await assert.rejects(restoring, /otra pestaña/)
  assert.equal(env.storage.getItem(SESSION_KEY), null)
})

test('logout waits for a pending refresh then revokes the latest refresh', async () => {
  let release, started
  const begin = new Promise((resolve) => { started = resolve })
  const deferred = new Promise((resolve) => { release = resolve })
  let revoked
  const env = setup(async (url, options) => {
    if (url.endsWith('/refresh/')) { started(); return deferred }
    if (url.endsWith('/logout/')) { revoked = options.body.refresh; return null }
    if (options.access === 'access-1') throw new ApiError(401)
    return profile
  })
  env.storage.setItem(SESSION_KEY, JSON.stringify({ id: 'shared', ...pair }))
  const a = env.create(), b = env.create()
  const restoring = a.restoreSession()
  await begin
  const loggingOut = b.logoutSession('shared')
  release({ access: 'rotated-access', refresh: 'rotated-refresh' })
  await restoring
  assert.deepEqual(await loggingOut, { revoked: true })
  assert.equal(revoked, 'rotated-refresh')
  assert.equal(env.storage.getItem(SESSION_KEY), null)
})

test('a new login does not reuse the preceding account refresh', async () => {
  let release, started
  const begin = new Promise((resolve) => { started = resolve })
  const deferred = new Promise((resolve) => { release = resolve })
  const newProfile = { ...profile, id: 2, username: 'otra_cuenta' }
  const env = setup(async (url, options) => {
    if (url.endsWith('/login/')) return { access: 'new-access', refresh: 'new-refresh' }
    if (url.endsWith('/refresh/')) { started(); return deferred }
    if (options.access === 'access-1') throw new ApiError(401)
    return options.access === 'new-access' ? newProfile : profile
  })
  env.storage.setItem(SESSION_KEY, JSON.stringify({ id: 'old-account', ...pair }))
  const restoring = env.create().restoreSession()
  await begin
  const loggingIn = env.create().loginSession('otra_cuenta', 'ficticia')
  release({ access: 'rotated-access', refresh: 'rotated-refresh' })
  await restoring
  assert.deepEqual((await loggingIn).user, newProfile)
  assert.equal(JSON.parse(env.storage.getItem(SESSION_KEY)).refresh, 'new-refresh')
})

test('lock wait expires and logout removes only its own session', async () => {
  const env = setup(async () => profile)
  env.storage.setItem(SESSION_KEY, JSON.stringify({ id: 'shared', ...pair }))
  const unavailableLocks = { request: (_name, { signal }) => new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new Error('aborted')))) }
  const service = createSessionService({ storage: () => env.storage, locks: () => unavailableLocks, lockTimeoutMs: 10 })
  await assert.rejects(service.logoutSession('shared'), /tiempo de espera/)
  assert.equal(env.storage.getItem(SESSION_KEY), null)
})

test('a late login cannot overwrite a new account', async () => {
  let release, started
  const begin = new Promise((resolve) => { started = resolve })
  const deferred = new Promise((resolve) => { release = resolve })
  const env = setup(async (url) => { if (url.endsWith('/login/')) { started(); return deferred }; return profile })
  const login = env.create().loginSession('cliente', 'ficticia')
  await begin
  env.storage.setItem(SESSION_KEY, JSON.stringify({ id: 'new-account', ...pair }))
  release(pair)
  await assert.rejects(login, /otra pestaña/)
  assert.equal(JSON.parse(env.storage.getItem(SESSION_KEY)).id, 'new-account')
})

test('HTTP timeout cancels a pending request and reports it', async () => {
  const http = createHttpClient({ baseUrl: 'http://localhost:8000/api', timeoutMs: 10, fetchImpl: (_url, { signal }) => new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new Error('aborted')))) })
  await assert.rejects(http('/auth/register/', { method: 'POST', body: { username: 'test' } }), /tiempo de espera/)
})

test('HTTP timeout also covers reading the response body', async () => {
  const http = createHttpClient({ baseUrl: 'http://localhost:8000/api', timeoutMs: 10, fetchImpl: async (_url, { signal }) => ({ ok: true, status: 200, json: () => new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new Error('aborted')))) }) })
  await assert.rejects(http('/auth/profile/'), /tiempo de espera/)
})

test('HTTP respects external cancellation and missing configuration', async () => {
  const controller = new AbortController()
  controller.abort()
  const http = createHttpClient({ baseUrl: 'http://localhost:8000/api', fetchImpl: (_url, { signal }) => signal.aborted ? Promise.reject(new Error('aborted')) : Promise.resolve() })
  await assert.rejects(http('/auth/profile/', { signal: controller.signal }), /cancelada/)
  await assert.rejects(createHttpClient()('/auth/login/'), /VITE_API_URL/)
})

test('registration sends backend fields and preserves server errors', async () => {
  const body = { username: 'cliente', email: 'cliente@example.test', password: 'ficticia', password_confirm: 'ficticia', telefono: '' }
  const http = createHttpClient({ baseUrl: 'http://localhost:8000/api', fetchImpl: async (_url, options) => {
    assert.deepEqual(JSON.parse(options.body), body)
    return { ok: false, status: 400, json: async () => ({ email: ['Correo duplicado.'] }) }
  } })
  await assert.rejects(http('/auth/register/', { method: 'POST', body }), (error) => error.status === 400 && error.data.email[0] === 'Correo duplicado.')
})
