import { useCallback, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { categories, createCommerceApi, products } from '../api/commerce.js'
import { useAuth } from '../auth/useAuth.js'
import { ErrorNotice, ResourceState, ShopLayout } from './shared.jsx'
import { money } from './utils.js'
import { useResource } from './useResource.js'

function AdminLinks() {
  const { user } = useAuth()
  return <nav className="shop-admin-links" aria-label="Administración"><Link to="/admin/productos">Productos</Link><Link to="/admin/inventario">Inventario</Link>{user.capacidades?.gestionar_pedidos && <Link to="/admin/pedidos">Pedidos</Link>}</nav>
}

const emptyProduct = { nombre: '', descripcion: '', precio: '', categoria: '', huevos_por_unidad: '', disponible: true }

export function AdminProducts() {
  const { api } = useAuth()
  const service = useMemo(() => createCommerceApi(api), [api])
  const loader = useCallback(() => Promise.all([products(), categories()]), [])
  const state = useResource(loader)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(emptyProduct)
  const [error, setError] = useState(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [image, setImage] = useState(null)
  const fileInput = useRef(null)
  function clearImage() { setImage(null); if (fileInput.current) fileInput.current.value = '' }
  function edit(item) { setEditing(item.id); setForm({ nombre: item.nombre, descripcion: item.descripcion, precio: item.precio, categoria: String(item.categoria), huevos_por_unidad: item.huevos_por_unidad ?? '', disponible: item.disponible }); clearImage(); setError(null); setMessage('') }
  function reset() { setEditing(null); setForm(emptyProduct); clearImage() }
  async function save(e) {
    e.preventDefault(); if (busy) return
    setBusy(true); setError(null); setMessage('')
    let data = { ...form, categoria: Number(form.categoria), huevos_por_unidad: form.huevos_por_unidad === '' ? null : Number(form.huevos_por_unidad) }
    if (image) {
      const multipart = new FormData()
      Object.entries(data).forEach(([key, value]) => multipart.append(key, value ?? ''))
      multipart.append('imagen', image)
      data = multipart
    }
    try { if (editing) await service.updateProduct(editing, data); else await service.createProduct(data); reset(); state.reload(); setMessage('Producto guardado.') } catch (err) { setError(err) } finally { setBusy(false) }
  }
  async function remove(item) {
    if (busy || !window.confirm(`¿Eliminar ${item.nombre}? Esta acción no se puede deshacer.`)) return
    setBusy(true); setError(null); setMessage('')
    try { await service.deleteProduct(item.id); if (editing === item.id) reset(); state.reload(); setMessage('Producto eliminado.') } catch (err) { setError(err) } finally { setBusy(false) }
  }
  return <ShopLayout eyebrow="Administración" title="PRODUCTOS"><AdminLinks /><ErrorNotice error={error} />{message && <p className="shop-success" role="status">{message}</p>}<ResourceState state={state}>
    <form className="shop-panel shop-form" onSubmit={save}><h2>{editing ? 'EDITAR PRODUCTO' : 'NUEVO PRODUCTO'}</h2><div className="row g-3"><div className="col-md-6"><label htmlFor="admin-name">Nombre</label><input id="admin-name" className="form-control" required maxLength="150" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></div><div className="col-md-6"><label htmlFor="admin-category">Categoría</label><select id="admin-category" className="form-select" required value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })}><option value="">Seleccionar</option>{state.data?.[1].map((c) => <option value={c.id} key={c.id}>{c.nombre}</option>)}</select></div><div className="col-12"><label htmlFor="admin-description">Descripción</label><textarea id="admin-description" className="form-control" value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} /></div><div className="col-md-6"><label htmlFor="admin-price">Precio</label><input id="admin-price" className="form-control" type="number" min="0" step="0.01" required value={form.precio} onChange={(e) => setForm({ ...form, precio: e.target.value })} /></div><div className="col-md-6"><label htmlFor="admin-eggs">Huevos por presentación</label><input id="admin-eggs" className="form-control" type="number" min="1" step="1" value={form.huevos_por_unidad} onChange={(e) => setForm({ ...form, huevos_por_unidad: e.target.value })} /><small>Sin configurar, no se podrá comprar.</small></div><div className="col-12"><label htmlFor="admin-image">Fotografía del producto</label><input ref={fileInput} id="admin-image" className="form-control" type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setImage(e.target.files[0] || null)} /><small>JPEG, PNG o WebP, hasta 5 MiB. Al editar, dejá el campo vacío para conservar la imagen actual.</small></div><div className="col-12"><label><input type="checkbox" checked={form.disponible} onChange={(e) => setForm({ ...form, disponible: e.target.checked })} /> Disponible</label></div></div><div className="shop-actions mt-3"><button className="shop-button" disabled={busy} type="submit">{busy ? 'GUARDANDO...' : 'GUARDAR'}</button>{editing && <button className="shop-outline" type="button" onClick={reset}>CANCELAR EDICIÓN</button>}</div></form>
    {state.data?.[0].length === 0 ? <p>No hay productos registrados.</p> : <div className="shop-list">{state.data?.[0].map((item) => <article className="shop-line" key={item.id}>{item.imagen_url && <img src={item.imagen_url} alt={`Fotografía de ${item.nombre}`} width="100" height="80" style={{ objectFit: 'contain' }} />}<div><h2>{item.nombre}</h2><p>{money(item.precio)} · {item.huevos_por_unidad ? `${item.huevos_por_unidad} huevos` : 'Presentación pendiente'} · {item.unidades_disponibles} disponibles</p></div><div className="shop-actions"><button className="shop-outline" type="button" disabled={busy} onClick={() => edit(item)}>EDITAR</button><button className="shop-outline" type="button" disabled={busy} onClick={() => remove(item)}>ELIMINAR</button></div></article>)}</div>}
  </ResourceState></ShopLayout>
}

export function AdminInventory() {
  const { api } = useAuth()
  const service = useMemo(() => createCommerceApi(api), [api])
  const loader = useCallback(async () => { try { return await service.inventory() } catch (error) { if (error.status === 404) return null; throw error } }, [service])
  const state = useResource(loader)
  const [quantity, setQuantity] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [message, setMessage] = useState('')
  async function save(e) {
    e.preventDefault(); const value = Number(quantity)
    if (busy || quantity === '' || !Number.isSafeInteger(value) || value < 0 || !window.confirm(`¿Establecer la reserva en ${value} huevos?`)) return
    setBusy(true); setError(null); setMessage('')
    try { await service.setInventory(value); state.reload(); setMessage('Reserva actualizada.'); setQuantity('') } catch (err) { setError(err) } finally { setBusy(false) }
  }
  return <ShopLayout eyebrow="Administración" title="RESERVA DE HUEVOS"><AdminLinks /><ErrorNotice error={error} />{message && <p className="shop-success" role="status">{message}</p>}<ResourceState state={state}><div className="shop-panel"><p>{state.data ? `Reserva actual: ${state.data.cantidad} huevos.` : 'La reserva todavía no está configurada.'}</p><p>Ingresá la cantidad real de huevos individuales.</p><form onSubmit={save}><label htmlFor="inventory-quantity">Nueva reserva</label><input id="inventory-quantity" className="form-control shop-quantity" type="number" min="0" max="2147483647" step="1" required value={quantity} onChange={(e) => setQuantity(e.target.value)} /><button className="shop-button mt-3" type="submit" disabled={busy}>{busy ? 'GUARDANDO...' : 'ACTUALIZAR RESERVA'}</button></form></div></ResourceState></ShopLayout>
}
