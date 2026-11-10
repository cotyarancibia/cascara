import { Link } from 'react-router-dom'
import { Navbar, Footer } from '../App.jsx'
import { errorMessage } from '../api/commerce.js'
import { canBuy, money } from './utils.js'

export function ShopLayout({ eyebrow, title, children }) {
  return <><Navbar /><main className="shop-page"><div className="container-fluid"><p className="shop-eyebrow">{eyebrow}</p><h1>{title}<span>.</span></h1>{children}</div></main><Footer /></>
}

export function ResourceState({ state, empty, children }) {
  if (state.loading) return <p role="status">Cargando...</p>
  if (state.error) return <div role="alert"><p>{errorMessage(state.error)}</p><button className="shop-button" type="button" onClick={state.reload}>REINTENTAR</button></div>
  if (empty) return <p>{empty}</p>
  return children
}

export function ProductImage({ image, name }) {
  return image ? <img className="shop-product-image" src={image} alt={name} /> : <div className="shop-placeholder" aria-hidden="true"><span>◯</span><small>CÁSCARA</small></div>
}

export function ProductCard({ item, onAdd, busy }) {
  return <article className="shop-card h-100"><ProductImage image={item.imagen_url} name={item.nombre} /><div className="shop-card-body"><p className="shop-eyebrow">{item.huevos_por_unidad ? `${item.huevos_por_unidad} huevos por presentación` : 'Presentación pendiente'}</p><h2>{item.nombre}</h2><p>{item.descripcion}</p><p className="shop-price">{money(item.precio)}</p><p>{canBuy(item) ? `${item.unidades_disponibles} disponibles` : 'No disponible'}</p><div className="shop-actions"><Link className="shop-link" to={`/productos/${item.id}`}>VER DETALLE →</Link>{onAdd && <button className="shop-button" type="button" onClick={() => onAdd(item, 1)} disabled={!canBuy(item) || busy}>AGREGAR</button>}</div></div></article>
}

export function ErrorNotice({ error }) { return error && <p className="shop-error" role="alert">{errorMessage(error)}</p> }

export function UncertainNotice({ destination }) {
  const cart = destination === 'cart'
  return <p className="shop-error" role="alert">No pudimos verificar el resultado. <Link to={cart ? '/carrito' : '/pedidos'}>{cart ? 'Revisá tu carrito' : 'Revisá tus pedidos'}</Link> antes de volver a intentar.</p>
}
