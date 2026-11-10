import { useCallback, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { createCommerceApi, isUncertainOutcome } from '../api/commerce.js'
import { useAuth } from '../auth/useAuth.js'
import { ErrorNotice, ResourceState, ShopLayout, UncertainNotice } from './shared.jsx'
import { money } from './utils.js'
import { useResource } from './useResource.js'

function useCart() {
  const { api } = useAuth()
  const service = useMemo(() => createCommerceApi(api), [api])
  const loader = useCallback(() => service.getCart(), [service])
  return { service, state: useResource(loader) }
}

export function Cart() {
  const { service, state } = useCart()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [message, setMessage] = useState('')
  async function change(action) {
    if (busy) return
    setBusy(true); setError(null); setMessage('')
    try { await action(); state.reload(); setMessage('Carrito actualizado.') } catch (e) { setError(e) } finally { setBusy(false) }
  }
  return <ShopLayout eyebrow="Tu selección" title="TU CARRITO"><ErrorNotice error={error} />{message && <p className="shop-success" role="status">{message}</p>}<ResourceState state={state} empty={state.data?.items.length === 0 ? 'Tu carrito está vacío.' : null}>
    <div className="shop-list">{state.data?.items.map((item) => <article className="shop-line" key={`${item.id}-${item.cantidad}`}><div><h2>{item.producto_detalle.nombre}</h2><p>{item.producto_detalle.huevos_por_unidad ? `${item.producto_detalle.huevos_por_unidad} huevos por presentación` : 'Presentación pendiente de configuración'}</p><p>Precio unitario: {money(item.producto_detalle.precio)}</p><p>{item.producto_detalle.disponible && item.producto_detalle.unidades_disponibles > 0 ? `${item.producto_detalle.unidades_disponibles} disponibles` : 'Producto no disponible'}</p></div><div><form className="shop-actions" onSubmit={(e) => { e.preventDefault(); const quantity = Number(new FormData(e.currentTarget).get('cantidad')); if (Number.isSafeInteger(quantity) && quantity > 0) change(() => service.updateItem(item.id, quantity)) }}><label htmlFor={`quantity-${item.id}`}>Cantidad</label><input id={`quantity-${item.id}`} name="cantidad" className="form-control shop-quantity" type="number" min="1" step="1" defaultValue={item.cantidad} required /><button className="shop-button" type="submit" disabled={busy}>ACTUALIZAR</button></form><button className="shop-link shop-text-button" type="button" disabled={busy} onClick={() => change(() => service.removeItem(item.id))}>Quitar producto</button></div></article>)}</div>
    <div className="shop-summary"><p>Subtotal actual: <strong>{state.data && money(state.data.subtotal_actual)}</strong></p><p>El precio y la disponibilidad se confirman al realizar el pedido.</p><Link className="shop-button" to="/checkout">CONTINUAR AL PEDIDO →</Link></div>
  </ResourceState><p className="mt-4"><Link className="shop-link" to="/productos">← SEGUIR MIRANDO</Link></p></ShopLayout>
}

export function Checkout() {
  const { service, state } = useCart()
  const [address, setAddress] = useState('')
  const [error, setError] = useState(null)
  const [pending, setPending] = useState(false)
  const [order, setOrder] = useState(null)
  const [uncertain, setUncertain] = useState(false)
  const submitting = useRef(false)
  async function submit(e) {
    e.preventDefault()
    if (submitting.current || uncertain || !address.trim() || !state.data?.items.length) return
    submitting.current = true; setPending(true); setError(null)
    try { setOrder(await service.confirm(state.data.id, address.trim())) }
    catch (err) { if (isUncertainOutcome(err)) setUncertain(true); else setError(err) }
    finally { submitting.current = false; setPending(false) }
  }
  return <ShopLayout eyebrow="Un paso más" title="CONFIRMAR PEDIDO">{order ? <div className="shop-panel" role="status"><h2>¡PEDIDO CONFIRMADO!</h2><p>Pedido #{order.id}</p><p>Total: <strong>{money(order.total)}</strong></p><p>La confirmación no implica un pago realizado.</p><Link className="shop-link" to="/pedidos">VER MIS PEDIDOS →</Link></div> : <><ErrorNotice error={error} />{uncertain && <UncertainNotice destination="orders" />}<ResourceState state={state} empty={state.data?.items.length === 0 ? 'Tu carrito está vacío.' : null}><div className="shop-panel"><ul>{state.data?.items.map((item) => <li key={item.id}>{item.cantidad} × {item.producto_detalle.nombre} · {money(item.producto_detalle.precio)} c/u</li>)}</ul><p>Subtotal actual: <strong>{state.data && money(state.data.subtotal_actual)}</strong></p><p>El importe final y la disponibilidad se calculan al confirmar.</p><form onSubmit={submit}><label htmlFor="delivery-address">Dirección de entrega</label><input className="form-control" id="delivery-address" value={address} onChange={(e) => setAddress(e.target.value)} maxLength="255" required /><button className="shop-button mt-3" disabled={pending || uncertain || !address.trim()} type="submit">{pending ? 'CONFIRMANDO...' : 'CONFIRMAR PEDIDO'}</button></form></div></ResourceState><p className="mt-4"><Link className="shop-link" to="/carrito">← VOLVER AL CARRITO</Link></p></>}</ShopLayout>
}
