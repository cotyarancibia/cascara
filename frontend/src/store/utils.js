export const money = (value) => new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(Number(value))
export const canBuy = (item) => Boolean(item?.disponible && item.huevos_por_unidad > 0 && item.unidades_disponibles > 0)

export function cartStockWarning(cart, inventory) {
  if (!Number.isInteger(inventory?.cantidad) || !Array.isArray(cart?.items)) return 'No pudimos comprobar la disponibilidad estimada del carrito.'
  if (cart.items.some((item) => !item.producto_detalle?.huevos_por_unidad)) return 'Hay productos sin presentación configurada en el carrito.'
  const eggs = cart.items.reduce((total, item) => total + item.cantidad * item.producto_detalle.huevos_por_unidad, 0)
  return eggs > inventory.cantidad ? `El carrito requiere ${eggs} huevos y la reserva estimada es de ${inventory.cantidad}.` : ''
}
