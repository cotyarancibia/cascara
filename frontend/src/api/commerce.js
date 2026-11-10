import { ApiError, request } from './http.js'

export const isUncertainOutcome = (error) => error?.status === 0 || (error?.status >= 500 && error.status < 600)

export function createCommerceApi(auth) {
  const getCart = async () => {
    const carts = await auth('/carritos/')
    if (!Array.isArray(carts)) throw new Error('La respuesta del carrito no es válida.')
    return carts[0] || auth('/carritos/', { method: 'POST', body: {} })
  }
  const updateItem = (id, cantidad) => auth(`/items-carrito/${id}/`, { method: 'PATCH', body: { cantidad } })
  return {
    getCart,
    updateItem,
    removeItem: (id) => auth(`/items-carrito/${id}/`, { method: 'DELETE' }),
    addItem: (producto, cantidad) => auth('/items-carrito/agregar/', { method: 'POST', body: { producto, cantidad } }),
    async confirm(id, direccion_entrega) {
      const order = await auth(`/carritos/${id}/confirmar/`, { method: 'POST', body: { direccion_entrega } })
      if (!Number.isSafeInteger(order?.id) || order.id < 1 || order.estado !== 'CONFIRMADO' || typeof order.total !== 'string' || !/^\d+\.\d{2}$/.test(order.total)) {
        throw new ApiError(0, null, 'La respuesta del pedido está incompleta.')
      }
      return order
    },
    orders: () => auth('/pedidos/'),
    updateOrder: (id, estado) => auth(`/pedidos/${id}/`, { method: 'PATCH', body: { estado } }),
    profile: () => auth('/auth/profile/'),
    inventory: () => auth('/inventario-huevos/'),
    setInventory: (cantidad) => auth('/inventario-huevos/', { method: 'PUT', body: { cantidad } }),
    createProduct: (data) => auth('/productos/', { method: 'POST', body: data }),
    updateProduct: (id, data) => auth(`/productos/${id}/`, { method: 'PATCH', body: data }),
    deleteProduct: (id) => auth(`/productos/${id}/`, { method: 'DELETE' }),
  }
}

export function createCatalogApi(publicRequest = request) {
  return {
    products: (params = '') => publicRequest(`/productos/${params}`),
    product: (id) => publicRequest(`/productos/${encodeURIComponent(id)}/`),
    categories: () => publicRequest('/categorias/'),
  }
}
export const { products, product, categories } = createCatalogApi()

export function errorMessage(error) {
  if (error?.status === 403) return 'No tenés permiso para realizar esta operación.'
  if (error?.status === 404) return 'No encontramos el recurso solicitado.'
  if (error?.status === 401) return 'La sesión venció. Iniciá sesión nuevamente.'
  const data = error?.data
  if (data && typeof data === 'object') {
    const messages = Object.values(data).flatMap((value) => Array.isArray(value) ? value : [value]).filter((value) => typeof value === 'string')
    if (messages.length) return messages.join(' ')
  }
  return error?.message || 'No se pudo completar la operación. Intentá nuevamente.'
}
