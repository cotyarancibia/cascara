import { useCallback, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { categories, createCommerceApi, isUncertainOutcome, product, products } from '../api/commerce.js'
import { useAuth } from '../auth/useAuth.js'
import { ErrorNotice, ProductCard, ProductImage, ResourceState, ShopLayout, UncertainNotice } from './shared.jsx'
import { canBuy, cartStockWarning, money } from './utils.js'
import { useResource } from './useResource.js'

function useAddToCart() {
  const { user, api } = useAuth()
  const service = useMemo(() => createCommerceApi(api), [api])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [message, setMessage] = useState('')
  const [warning, setWarning] = useState('')
  const [uncertain, setUncertain] = useState(false)
  async function add(item, cantidad) {
    if (busy || uncertain || !canBuy(item) || !Number.isSafeInteger(cantidad) || cantidad < 1 || cantidad > item.unidades_disponibles) return
    setBusy(true); setError(null); setMessage(''); setWarning('')
    try {
      await service.addItem(item.id, cantidad)
      setMessage('Agregado al carrito. La disponibilidad se confirma al comprar.')
      try { const [cart, inventory] = await Promise.all([service.getCart(), service.inventory()]); setWarning(cartStockWarning(cart, inventory)) }
      catch { setWarning('No pudimos comprobar la disponibilidad estimada del carrito.') }
    }
    catch (e) { if (isUncertainOutcome(e)) setUncertain(true); else setError(e) }
    finally { setBusy(false) }
  }
  return { add: user?.role === 'CLIENTE' ? add : null, busy: busy || uncertain, error, message, warning, uncertain }
}

export function Catalog() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [available, setAvailable] = useState('')
  const [query, setQuery] = useState('')
  const loader = useCallback(() => Promise.all([products(query), categories()]), [query])
  const state = useResource(loader)
  const cart = useAddToCart()
  function submit(event) {
    event.preventDefault()
    const params = new URLSearchParams()
    if (search.trim()) params.set('search', search.trim())
    if (category) params.set('categoria', category)
    if (available) params.set('disponible', available)
    setQuery(params.size ? `?${params}` : '')
    if (query === (params.size ? `?${params}` : '')) state.reload()
  }
  return <ShopLayout eyebrow="Del campo a tu mesa" title="NUESTRA TIENDA">
    <form className="shop-filter" onSubmit={submit}><div><label htmlFor="catalog-search">Buscar productos</label><input id="catalog-search" className="form-control" value={search} onChange={(e) => setSearch(e.target.value)} /></div><div><label htmlFor="catalog-category">Categoría</label><select id="catalog-category" className="form-select" value={category} onChange={(e) => setCategory(e.target.value)}><option value="">Todas</option>{state.data?.[1].map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</select></div><div><label htmlFor="catalog-availability">Disponibilidad</label><select id="catalog-availability" className="form-select" value={available} onChange={(e) => setAvailable(e.target.value)}><option value="">Todos</option><option value="true">Disponibles</option><option value="false">No disponibles</option></select></div><button className="shop-button" type="submit">BUSCAR</button></form>
    <ErrorNotice error={cart.error} />{cart.uncertain && <UncertainNotice destination="cart" />}{cart.message && <p className="shop-success" role="status">{cart.message} <Link to="/carrito">Ver carrito</Link></p>}{cart.warning && <p role="alert">{cart.warning}</p>}
    <ResourceState state={state} empty={state.data?.[0].length === 0 ? 'No encontramos productos para mostrar.' : null}><div className="row g-4">{state.data?.[0].map((item) => <div className="col-md-6 col-xl-4" key={item.id}><ProductCard item={item} onAdd={cart.add} busy={cart.busy} /></div>)}</div></ResourceState>
  </ShopLayout>
}

export function ProductDetail() {
  const { id } = useParams()
  const loader = useCallback(() => product(id), [id])
  const state = useResource(loader)
  const cart = useAddToCart()
  const [cantidad, setCantidad] = useState('1')
  const item = state.data
  const amount = Number(cantidad)
  const valid = Number.isSafeInteger(amount) && amount > 0 && amount <= (item?.unidades_disponibles || 0)
  return <ShopLayout eyebrow="Nuestra tienda" title="DETALLE DEL PRODUCTO"><Link className="shop-link" to="/productos">← VOLVER AL CATÁLOGO</Link><ResourceState state={state}><div className="row g-4 mt-2 align-items-center"><div className="col-lg-5"><ProductImage image={item?.imagen_url} name={item?.nombre} /></div><div className="col-lg-7"><h2>{item?.nombre}</h2><p>{item?.descripcion}</p><p className="shop-price">{item && money(item.precio)}</p><p>{item?.huevos_por_unidad ? `${item.huevos_por_unidad} huevos por presentación` : 'Presentación pendiente de configuración'}</p><p>{canBuy(item) ? `${item.unidades_disponibles} disponibles` : 'No disponible'}</p>{cart.add && <form onSubmit={(e) => { e.preventDefault(); cart.add(item, amount) }}><label htmlFor="product-quantity">Cantidad</label><input id="product-quantity" className="form-control shop-quantity" type="number" min="1" max={item?.unidades_disponibles || 1} step="1" value={cantidad} onChange={(e) => setCantidad(e.target.value)} /><button className="shop-button mt-3" type="submit" disabled={!valid || !canBuy(item) || cart.busy}>AGREGAR AL CARRITO</button></form>}<ErrorNotice error={cart.error} />{cart.uncertain && <UncertainNotice destination="cart" />}{cart.message && <p className="shop-success" role="status">{cart.message} <Link to="/carrito">Ver carrito</Link></p>}{cart.warning && <p role="alert">{cart.warning}</p>}</div></div></ResourceState></ShopLayout>
}
