import test from 'node:test'
import assert from 'node:assert/strict'
import { createCatalogApi, createCommerceApi, errorMessage, isUncertainOutcome } from '../src/api/commerce.js'
import { canAccess } from '../src/auth/permissions.js'
import { ApiError } from '../src/api/http.js'
import { cartStockWarning } from '../src/store/utils.js'

test('catalog returns real response, handles empty and passes supported filters', async () => {
  const paths = []
  const api = createCatalogApi(async (path) => { paths.push(path); return path.includes('search=') ? [{ id: 1 }] : [] })
  assert.deepEqual(await api.products(), [])
  assert.deepEqual(await api.products('?search=huevos'), [{ id: 1 }])
  assert.deepEqual(paths, ['/productos/', '/productos/?search=huevos'])
})

test('product detail propagates not-found and connection errors', async () => {
  const api = createCatalogApi(async () => { throw new ApiError(404, null) })
  await assert.rejects(api.product(99), (error) => error.status === 404)
  assert.match(errorMessage(new ApiError(404)), /No encontramos/)
  assert.match(errorMessage(new Error('Sin conexión')), /Sin conexión/)
})

test('cart adds items with one atomic server request', async () => {
  const calls = []
  const api = createCommerceApi(async (path, options = {}) => { calls.push([path, options]); if (path === '/carritos/' && !options.method) return []; if (path === '/carritos/') return { id: 4, items: [] }; return { id: 3 } })
  await api.addItem(5, 2)
  assert.deepEqual(calls.map(([path]) => path), ['/items-carrito/agregar/'])
  assert.deepEqual(calls[0][1].body, { producto: 5, cantidad: 2 })
})

test('cart propagates atomic addition errors without retry', async () => {
  let calls = 0
  const api = createCommerceApi(async () => { calls++; throw new ApiError(400, { cantidad: ['Inválida'] }) })
  await assert.rejects(api.addItem(5, 3), (error) => error.status === 400)
  assert.equal(calls, 1)
})

test('cart modification, removal and checkout use server endpoints', async () => {
  const calls = []
  const api = createCommerceApi(async (path, options = {}) => { calls.push([path, options]); if (path.includes('confirmar')) return { id: 42, total: '100.00', estado: 'CONFIRMADO' }; return null })
  await api.updateItem(7, 2)
  await api.removeItem(7)
  assert.equal((await api.confirm(1, 'Calle')).id, 42)
  assert.deepEqual(calls.map(([path]) => path), ['/items-carrito/7/', '/items-carrito/7/', '/carritos/1/confirmar/'])
  assert.deepEqual(calls[2][1].body, { direccion_entrega: 'Calle' })
})

test('checkout failure is propagated without retry', async () => {
  let calls = 0
  const api = createCommerceApi(async () => { calls++; throw new ApiError(400, { detail: 'Stock insuficiente.' }) })
  await assert.rejects(api.confirm(1, 'Calle'), (error) => errorMessage(error).includes('Stock insuficiente'))
  assert.equal(calls, 1)
})

test('network and proxy failures are uncertain but validation failures are not', () => {
  for (const status of [0, 500, 502, 503, 504]) assert.equal(isUncertainOutcome(new ApiError(status)), true)
  for (const status of [400, 401, 403, 404]) assert.equal(isUncertainOutcome(new ApiError(status)), false)
})

test('uncertain add and checkout failures do not retry', async () => {
  for (const status of [0, 500, 502, 503, 504]) {
    for (const operation of ['add', 'checkout']) {
      let calls = 0
      const api = createCommerceApi(async () => { calls++; throw new ApiError(status) })
      await assert.rejects(operation === 'add' ? api.addItem(1, 1) : api.confirm(1, 'Calle'), (error) => isUncertainOutcome(error))
      assert.equal(calls, 1)
    }
  }
})

test('checkout treats an incomplete successful response as uncertain', async () => {
  const api = createCommerceApi(async () => ({ id: 42 }))
  await assert.rejects(api.confirm(1, 'Calle'), (error) => error.status === 0)
})

test('cart warning counts eggs across different presentations', () => {
  const cart = { items: [{ cantidad: 2, producto_detalle: { huevos_por_unidad: 6 } }, { cantidad: 1, producto_detalle: { huevos_por_unidad: 30 } }] }
  assert.match(cartStockWarning(cart, { cantidad: 40 }), /42 huevos/)
  assert.equal(cartStockWarning(cart, { cantidad: 42 }), '')
})

test('role guard restricts client, seller and admin routes', () => {
  assert.equal(canAccess(null), false)
  assert.equal(canAccess({ role: 'CLIENTE' }, ['CLIENTE']), true)
  assert.equal(canAccess({ role: 'CLIENTE' }, ['ADMIN', 'VENDEDOR']), false)
  assert.equal(canAccess({ role: 'VENDEDOR' }, ['ADMIN', 'VENDEDOR']), true)
  assert.equal(canAccess({ role: 'VENDEDOR' }, ['ADMIN']), false)
  assert.equal(canAccess({ role: 'ADMIN' }, ['ADMIN']), true)
  assert.equal(canAccess({ role: 'CLIENTE', capacidades: { gestionar_productos: true, gestionar_pedidos: true } }, ['ADMIN']), true)
})

test('order history and profile use authenticated endpoints', async () => {
  const paths = []
  const api = createCommerceApi(async (path) => { paths.push(path); return [] })
  await api.orders(); await api.profile()
  assert.deepEqual(paths, ['/pedidos/', '/auth/profile/'])
})
