export class ApiError extends Error {
  constructor(status, data, message = 'La solicitud no pudo completarse.') {
    super(message)
    this.status = status
    this.data = data
  }
}

export function createHttpClient({ baseUrl, fetchImpl = globalThis.fetch, timeoutMs = 10000 } = {}) {
  return async function request(path, { method = 'GET', body, access, signal } = {}) {
    let url
    try {
      url = new URL(baseUrl)
      if (!['http:', 'https:'].includes(url.protocol) || !url.pathname.replace(/\/$/, '').endsWith('/api') || url.search || url.hash) throw new Error()
    } catch {
      throw new ApiError(0, null, 'Configurá VITE_API_URL con una URL válida que termine en /api.')
    }
    const controller = new AbortController()
    let timedOut = false
    const cancel = () => controller.abort()
    if (signal?.aborted) cancel()
    else signal?.addEventListener('abort', cancel, { once: true })
    const timer = setTimeout(() => { timedOut = true; controller.abort() }, timeoutMs)
    try {
      const response = await fetchImpl(`${url.href.replace(/\/$/, '')}${path}`, {
        method,
        headers: { ...(body ? { 'Content-Type': 'application/json' } : {}), ...(access ? { Authorization: `Bearer ${access}` } : {}) },
        ...(body ? { body: JSON.stringify(body) } : {}),
        signal: controller.signal,
      })
      let data = null
      if (response.status !== 205 && response.status !== 204) {
        try { data = await response.json() } catch (error) { if (controller.signal.aborted) throw error }
      }
      if (!response.ok) throw new ApiError(response.status, data)
      return data
    } catch (error) {
      if (error instanceof ApiError) throw error
      if (timedOut) throw new ApiError(0, null, 'La conexión agotó el tiempo de espera. Intentá nuevamente.')
      if (signal?.aborted) throw new ApiError(0, null, 'La solicitud fue cancelada.')
      throw new ApiError(0, null, 'No se pudo conectar con el servidor. Intentá nuevamente.')
    } finally {
      clearTimeout(timer)
      signal?.removeEventListener('abort', cancel)
    }
  }
}

export const request = createHttpClient({ baseUrl: import.meta.env?.VITE_API_URL })
