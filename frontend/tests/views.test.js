import { after, before, test } from 'node:test'
import assert from 'node:assert/strict'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'

let server, ResourceState, ProductCard, ProductImage, HomeProductsGrid, UncertainNotice, AdminOrderContact
before(async () => {
  server = await createServer({ configFile: false, envDir: false, plugins: [react()], server: { middlewareMode: true }, appType: 'custom' })
  ;({ ResourceState, ProductCard, ProductImage, UncertainNotice } = await server.ssrLoadModule('/src/store/shared.jsx'))
  ;({ HomeProductsGrid } = await server.ssrLoadModule('/src/App.jsx'))
  ;({ AdminOrderContact } = await server.ssrLoadModule('/src/store/Account.jsx'))
})
after(async () => { await server?.close() })

test('resource views communicate loading, empty and API errors with retry', () => {
  const render = (state, empty) => renderToStaticMarkup(React.createElement(ResourceState, { state, empty }, 'Contenido'))
  assert.match(render({ loading: true }), /Cargando/)
  assert.match(render({ loading: false }, 'Sin productos'), /Sin productos/)
  const error = render({ loading: false, error: new Error('Sin conexión'), reload() {} })
  assert.match(error, /role="alert"/)
  assert.match(error, /REINTENTAR/)
})

test('product card displays server data and disables unavailable products', () => {
  const item = { id: 42, nombre: 'Presentación de prueba', descripcion: 'Descripción', precio: '100.00', huevos_por_unidad: 6, unidades_disponibles: 0, disponible: true }
  const html = renderToStaticMarkup(React.createElement(MemoryRouter, null, React.createElement(ProductCard, { item, onAdd() {} })))
  assert.match(html, /Presentación de prueba/)
  assert.match(html, /No disponible/)
  assert.match(html, /disabled/)
  assert.match(html, /\/productos\/42/)
})

test('home shows API product and image or empty state', () => {
  const state = { loading: false, error: null, data: [{ id: 5, nombre: 'Producto real', descripcion: 'Descripción real', huevos_por_unidad: 6, imagen_url: 'http://localhost:8000/media/productos/foto.png' }] }
  const html = renderToStaticMarkup(React.createElement(HomeProductsGrid, { state }))
  assert.match(html, /Producto real/)
  assert.match(html, /\/media\/productos\/foto.png/)
  assert.match(renderToStaticMarkup(React.createElement(HomeProductsGrid, { state: { ...state, data: [] } })), /no hay productos disponibles/)
})

test('catalog and detail image uses API URL and accessible text, with a fallback', () => {
  const props = { image: 'http://localhost:8000/media/productos/foto.png', name: 'Huevos de prueba' }
  const html = renderToStaticMarkup(React.createElement(ProductImage, props))
  assert.match(html, /\/media\/productos\/foto.png/)
  assert.match(html, /alt="Huevos de prueba"/)
  assert.match(renderToStaticMarkup(React.createElement(ProductImage, { name: props.name })), /shop-placeholder/)
})

test('uncertain outcomes provide accessible links to the relevant history', () => {
  for (const [destination, path, label] of [['cart', '/carrito', 'Revisá tu carrito'], ['orders', '/pedidos', 'Revisá tus pedidos']]) {
    const html = renderToStaticMarkup(React.createElement(MemoryRouter, null, React.createElement(UncertainNotice, { destination })))
    assert.match(html, /No pudimos verificar el resultado/)
    assert.ok(html.includes(`href="${path}"`) && html.includes(label))
  }
})

test('administrative order contact shows supplied details and missing phone', () => {
  const contact = { username: 'cliente-ficticio', email: 'cliente@example.test', telefono: '' }
  const html = renderToStaticMarkup(React.createElement(AdminOrderContact, { contact }))
  assert.match(html, /cliente-ficticio/)
  assert.match(html, /cliente@example.test/)
  assert.match(html, /Teléfono: No informado/)
  const withPhone = renderToStaticMarkup(React.createElement(AdminOrderContact, { contact: { ...contact, telefono: '123456' } }))
  assert.match(withPhone, /Teléfono: 123456/)
})
