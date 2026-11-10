import { useCallback, useMemo, useState } from 'react'
import { createCommerceApi } from '../api/commerce.js'
import { useAuth } from '../auth/useAuth.js'
import { ErrorNotice, ResourceState, ShopLayout } from './shared.jsx'
import { money } from './utils.js'
import { useResource } from './useResource.js'

export function Orders({ admin = false }) {
  const { api } = useAuth()
  const service = useMemo(() => createCommerceApi(api), [api])
  const loader = useCallback(() => service.orders(), [service])
  const state = useResource(loader)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  async function update(order, estado) {
    if (busy || !window.confirm(`¿Cambiar el pedido #${order.id} a ${estado}?`)) return
    setBusy(true); setError(null); setMessage('')
    try { await service.updateOrder(order.id, estado); state.reload(); setMessage('Estado actualizado.') } catch (e) { setError(e) } finally { setBusy(false) }
  }
  return <ShopLayout eyebrow={admin ? 'Administración' : 'Tu historia con Cáscara'} title={admin ? 'PEDIDOS' : 'MIS PEDIDOS'}><ErrorNotice error={error} />{message && <p className="shop-success" role="status">{message}</p>}<ResourceState state={state} empty={state.data?.length === 0 ? 'Todavía no hay pedidos para mostrar.' : null}><div className="shop-list">{state.data?.map((order) => <article className="shop-panel" key={order.id}><h2>PEDIDO #{order.id}</h2><p>{new Date(order.fecha_pedido).toLocaleString('es-AR')} · {order.estado}</p><p>Entrega: {order.direccion_entrega}</p><ul>{order.items.map((item) => <li key={item.id}>{item.cantidad} × {item.producto_nombre} · {money(item.precio_unitario)} c/u{item.huevos_por_unidad ? ` · ${item.huevos_por_unidad} huevos` : ''}</li>)}</ul><p>Total: <strong>{money(order.total)}</strong></p>{admin && <div className="shop-actions">{order.estado === 'CONFIRMADO' && <button className="shop-button" type="button" disabled={busy} onClick={() => update(order, 'ENTREGADO')}>MARCAR ENTREGADO</button>}{(order.estado === 'PENDIENTE' || (order.estado === 'CONFIRMADO' && order.huevos_descontados !== null)) && <button className="shop-outline" type="button" disabled={busy} onClick={() => update(order, 'CANCELADO')}>CANCELAR PEDIDO</button>}{order.estado === 'CONFIRMADO' && order.huevos_descontados === null && <p>Pedido histórico: la cancelación requiere revisión manual.</p>}</div>}</article>)}</div></ResourceState></ShopLayout>
}

export function Profile() {
  const { api, saveProfile } = useAuth()
  const service = useMemo(() => createCommerceApi(api), [api])
  const loader = useCallback(() => service.profile(), [service])
  const state = useResource(loader)
  return <ShopLayout eyebrow="Tu cuenta" title="MI PERFIL"><ResourceState state={state}>{state.data && <ProfileForm key={state.data.id} profile={state.data} save={saveProfile} />}</ResourceState></ShopLayout>
}

function ProfileForm({ profile, save }) {
  const [form, setForm] = useState({ email: profile.email, telefono: profile.telefono, direccion: profile.direccion })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [success, setSuccess] = useState('')
  async function submit(e) {
    e.preventDefault(); if (busy) return
    setBusy(true); setError(null); setSuccess('')
    try { await save(form); setSuccess('Perfil actualizado.') } catch (err) { setError(err) } finally { setBusy(false) }
  }
  const fields = [['email', 'Correo electrónico', 'email'], ['telefono', 'Teléfono', 'tel'], ['direccion', 'Dirección', 'text']]
  return <form className="shop-panel shop-form" onSubmit={submit}><p>Usuario: <strong>{profile.username}</strong></p>{fields.map(([name, label, type]) => <div key={name}><label htmlFor={`profile-${name}`}>{label}</label><input className="form-control" id={`profile-${name}`} type={type} value={form[name] || ''} onChange={(e) => setForm({ ...form, [name]: e.target.value })} required={name === 'email'} aria-invalid={Boolean(error?.data?.[name]) || undefined} aria-describedby={error?.data?.[name] ? `profile-error-${name}` : undefined} />{error?.data?.[name] && <p className="shop-error" id={`profile-error-${name}`}>{[].concat(error.data[name]).join(' ')}</p>}</div>)}<ErrorNotice error={error} />{success && <p className="shop-success" role="status">{success}</p>}<button className="shop-button" type="submit" disabled={busy}>{busy ? 'GUARDANDO...' : 'GUARDAR CAMBIOS'}</button></form>
}
