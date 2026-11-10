import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from './auth/useAuth.js'

// Número en formato internacional, solo dígitos y sin el signo +.
const WHATSAPP_NUMBER = '5492395408745'
const WHATSAPP_MESSAGE = '¡Hola! Quisiera consultar sobre los huevos de campo de Cáscara.'

const links = [
  ['Inicio', '#inicio'],
  ['Nosotros', '#nosotros'],
  ['Productos', '#productos'],
  ['Recetas', '#recetas'],
  ['Contacto', '#contacto'],
]

const products = [
  { number: '01', name: 'Media docena', amount: '6 huevos', description: 'Para los pequeños grandes momentos.', image: '/images/media-docena.png' },
  { number: '02', name: 'Docena', amount: '12 huevos', description: 'El clásico que nunca puede faltar.', image: '/images/docena.png' },
  { number: '03', name: 'Maple', amount: '30 huevos', description: 'Para compartir alrededor de la mesa.', image: '/images/maple-30-huevos.png' },
]

const heroImages = [
  '/images/hero-eggs-hero.webp', '/images/farm-hens-hero.webp', '/images/hero-hens-field-hero.webp',
  '/images/hero-egg-red-hero.webp', '/images/hero-fried-egg-hero.webp', '/images/hero-henhouse-hero.webp',
]

const recipes = [
  { name: 'Huevos revueltos cremosos', image: '/images/recipe-eggs.png' },
  { name: 'Chipá', image: '/images/recipe-chipa.png' },
  { name: 'Wrap de huevo con pollo y palta', image: '/images/recipe-wrap.png' },
  { name: 'Pancakes de banana', image: '/images/recipe-pancakes.png' },
  { name: 'Omelette de verduras', image: '/images/recipe-omelette.png' },
  { name: 'Tortilla de papa', image: '/images/recipe-tortilla.png' },
]

function useReducedMotion() {
  const [reduced, setReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = (event) => setReduced(event.matches)
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])
  return reduced
}

function useAutoAdvance(advance, paused) {
  useEffect(() => {
    if (paused) return undefined
    const timer = window.setInterval(advance, 5000)
    return () => window.clearInterval(timer)
  }, [advance, paused])
}

function Icon({ name, className = '' }) {
  const paths = {
    user: <><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 3.5-6 8-6s8 2 8 6" /></>,
    cart: <><path d="M3 4h2l2.2 10h10.9l2-7H6" /><circle cx="9" cy="19" r="1" /><circle cx="17" cy="19" r="1" /></>,
    sun: <path d="M12 2C8 2 4.5 10.4 4.5 15a7.5 7.5 0 0 0 15 0C19.5 10.4 16 2 12 2Z" />,
    leaf: <><path d="M20 4C10 4 4 8 4 15c0 3 2 5 5 5 7 0 11-6 11-16Z" /><path d="M4 20c3-4 6-6 11-9" /></>,
    heart: <path d="M20.8 5.8c-2-2-5.2-1.8-6.9.3L12 8.2l-1.9-2.1C8.4 4 5.2 3.8 3.2 5.8c-2 2-1.8 5.2.2 7.2L12 21l8.6-8c2-2 2.2-5.2.2-7.2Z" />,
    whatsapp: <><path d="M20.5 11.7a8.5 8.5 0 0 1-12.7 7.4L3 20.5l1.4-4.6a8.5 8.5 0 1 1 16.1-4.2Z" /><path d="M8.1 8.1c.3-.3.6-.3.9-.1l1 1.4c.2.3.1.6-.2.9l-.5.5c.5 1.1 1.6 2.1 2.7 2.6l.5-.5c.2-.3.5-.3.8-.1l1.5.9c.3.2.3.5.1.8-.4.7-1.1 1-1.8.9-2.4-.5-5.1-3.1-5.6-5.5-.1-.7.1-1.3.6-1.8Z" /></>,
    arrow: <><path d="M4 12h15" /><path d="m14 7 5 5-5 5" /></>,
  }
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}

function Brand({ light = false }) {
  return <a className={`brand ${light ? 'brand-light' : ''}`} href="#inicio" aria-label="Cáscara, volver al inicio">cás<span className="brand-crack">c</span>ara<span>.</span></a>
}

function AccountMenu({ mobile = false }) {
  const [open, setOpen] = useState(false)
  const menuRef = useRef(null)
  const buttonRef = useRef(null)
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const menuId = mobile ? 'account-menu-mobile' : 'account-menu-desktop'

  useEffect(() => {
    if (!open) return undefined
    function closeOnOutsideClick(event) {
      if (!menuRef.current?.contains(event.target)) setOpen(false)
    }
    function closeOnEscape(event) {
      if (event.key === 'Escape') {
        setOpen(false)
        buttonRef.current?.focus()
      }
    }
    document.addEventListener('pointerdown', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsideClick)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [open])

  if (!user) return null

  return <div className={`account-menu${mobile ? ' account-menu-mobile' : ''}`} ref={menuRef} onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false) }}>
    <button ref={buttonRef} className="nav-user-button" type="button" onClick={() => setOpen((current) => !current)} aria-label="Mi cuenta" aria-expanded={open} aria-controls={open ? menuId : undefined}>
      <Icon name="user" />{mobile && <span>MI CUENTA</span>}
    </button>
    {open && <div className="account-panel" id={menuId}>
      <p>{user.email}</p>
      <button type="button" onClick={() => { void logout(); navigate('/login', { replace: true }) }}>Cerrar sesión</button>
    </div>}
  </div>
}

function Navbar() {
  const [open, setOpen] = useState(false)
  return (
    <header className="site-header" id="inicio">
      <nav className="navbar navbar-expand-lg site-nav container-fluid" aria-label="Navegación principal">
        <Brand />
        <button className="navbar-toggler nav-toggle" type="button" aria-label={open ? 'Cerrar menú' : 'Abrir menú'} aria-expanded={open} aria-controls="main-menu" onClick={() => setOpen(!open)}>
          <span></span><span></span><span></span>
        </button>
        <div className={`collapse navbar-collapse ${open ? 'show' : ''}`} id="main-menu">
          <ul className="navbar-nav mx-auto align-items-lg-center">
            {links.map(([label, href]) => <li className="nav-item" key={href}><a className="nav-link" href={href} onClick={() => setOpen(false)}>{label}</a></li>)}
            <li className="nav-item d-lg-none"><AccountMenu mobile /></li>
          </ul>
          <div className="nav-icons d-none d-lg-flex" aria-label="Opciones de usuario y carrito">
            <AccountMenu /><span title="Carrito próximamente"><Icon name="cart" /></span>
          </div>
        </div>
      </nav>
    </header>
  )
}

function Hero() {
  const [slide, setSlide] = useState(0)
  const [paused, setPaused] = useState(false)
  const reduced = useReducedMotion()
  useAutoAdvance(() => setSlide((current) => (current + 1) % heroImages.length), paused || reduced)
  return (
    <section className="hero" aria-labelledby="hero-title">
      {heroImages.map((image, index) => {
        const adjacent = index === (slide + 1) % heroImages.length || index === (slide + heroImages.length - 1) % heroImages.length
        return (index === slide || adjacent) && <img key={image} className={`hero-image ${index === slide ? 'is-active' : ''}`} src={image} alt="" aria-hidden="true" fetchPriority={index === 0 ? 'high' : 'auto'} />
      })}
      <div className="hero-overlay"></div>
      <div className="hero-content container-fluid">
        <h1 id="hero-title">HUEVOS DE GALLINAS LIBRES<br className="d-none d-md-block" /> DE JAULA, POSTA.</h1>
        <a href="#productos" className="pill-button pill-light">CONOCÉ NUESTROS PRODUCTOS <Icon name="arrow" /></a>
      </div>
      {!reduced && <button className="carousel-pause hero-pause" type="button" onClick={() => setPaused(!paused)}>{paused ? 'Reproducir' : 'Pausar'} fotografías</button>}
    </section>
  )
}

function Benefits() {
  const benefits = [
    { icon: 'sun', title: 'Frescura natural', copy: 'Para acompañar cada comida del día.' },
    { icon: 'leaf', title: 'Gallinas de campo', copy: 'Huevos que nos acercan al campo.' },
    { icon: 'heart', title: 'Calidad en cada huevo', copy: 'El sabor de elegir lo simple.' },
  ]
  return (
    <section className="benefits section-pad" aria-labelledby="benefits-title">
      <div className="container-fluid">
        <div className="section-heading d-flex flex-wrap justify-content-between align-items-end gap-2">
          <div><p className="eyebrow">Lo bueno de lo simple</p><h2 id="benefits-title">HAY COSAS QUE<br className="d-none d-md-block" /> SE NOTAN<span>.</span></h2></div>
          <p className="section-intro">Un pequeño ingrediente.<br />Un montón de buenos momentos.</p>
        </div>
        <div className="row g-0 benefit-row">
          {benefits.map((benefit, i) => <div className="col-md-4" key={benefit.title}><article className="benefit-card"><div className="benefit-top"><Icon name={benefit.icon} /><span>0{i + 1}</span></div><h3>{benefit.title}</h3><p>{benefit.copy}</p></article></div>)}
        </div>
      </div>
    </section>
  )
}

function IdentityStrip() {
  const message = 'NO ELIJAS CUALQUIER HUEVO. ELEGÍ LOS DE CÁSCARA.'
  return <div className="identity-strip" aria-label={message}><div className="identity-track" aria-hidden="true">{[0, 1].map((group) => <div className="identity-group" key={group}>{Array.from({ length: 8 }, (_, item) => <span key={item}>{message}</span>)}</div>)}</div></div>
}

function Products() {
  return (
    <section className="products section-pad" id="productos" aria-labelledby="products-title">
      <div className="container-fluid">
        <div className="row align-items-end product-header"><div className="col-lg-7"><p className="eyebrow">Para todos los días</p><h2 id="products-title">ELEGÍ TUS<br />HUEVOS<span>.</span></h2></div><div className="col-lg-5"><p className="products-intro">En la medida justa para tus recetas, tus desayunos y todo lo que se comparte.</p></div></div>
        <div className="row g-3 g-xl-4 product-grid">
          {products.map((product) => <div className="col-md-4" key={product.name}><article className="product-card h-100"><div className="product-card-top"><span>CAMPO / {product.number}</span></div><div className="product-photo"><img src={product.image} alt={`Huevera con ${product.amount}`} /></div><div className="product-info"><div><p className="product-amount">{product.amount}</p><h3>{product.name}</h3><p>{product.description}</p></div></div></article></div>)}
        </div>
      </div>
    </section>
  )
}

function Recipes() {
  const [slide, setSlide] = useState(0)
  const [animated, setAnimated] = useState(true)
  const [paused, setPaused] = useState(false)
  const reduced = useReducedMotion()
  const trackRef = useRef(null)
  useAutoAdvance(() => {
    if (slide >= recipes.length) {
      setAnimated(false)
      setSlide(0)
    } else {
      setAnimated(true)
      setSlide(slide + 1)
    }
  }, paused || reduced)

  useEffect(() => {
    const track = trackRef.current
    function handleCancel(event) {
      if (event.target === track && event.propertyName === 'transform' && slide >= recipes.length) {
        setAnimated(false)
        setSlide(0)
      }
    }
    track.addEventListener('transitioncancel', handleCancel)
    return () => track.removeEventListener('transitioncancel', handleCancel)
  }, [slide])

  function finishTransition(event) {
    if (event.target === event.currentTarget && event.propertyName === 'transform' && slide >= recipes.length) {
      setAnimated(false)
      setSlide(0)
    }
  }

  function navigate(direction) {
    setAnimated(false)
    setSlide((current) => (current % recipes.length + direction + recipes.length) % recipes.length)
  }

  return (
    <section className="recipes section-pad" id="recetas" aria-labelledby="recipes-title">
      <div className="container-fluid"><h2 id="recipes-title">QUE CÁSCARA ESTÉ EN TU PRÓXIMA RECETA</h2>
        <div className="recipe-viewport" aria-label="Ideas de recetas">
          <div ref={trackRef} className={`recipe-track ${animated ? '' : 'without-transition'}`} style={{ transform: `translateX(calc(-${slide} * (var(--recipe-card-width) + 1rem)))` }} onTransitionEnd={finishTransition}>
            {[...recipes, recipes[0]].map((recipe, index) => <article className="recipe-card" key={`${recipe.name}-${index}`} aria-hidden={index === recipes.length}><img src={recipe.image} alt={recipe.name} loading="lazy" /><h3>{recipe.name}</h3></article>)}
          </div>
        </div>
        {reduced ? <div className="recipe-controls" aria-label="Navegación de recetas"><button className="carousel-pause" type="button" onClick={() => navigate(-1)} aria-label="Receta anterior">Anterior</button><span aria-live="polite">{slide % recipes.length + 1} / {recipes.length}</span><button className="carousel-pause" type="button" onClick={() => navigate(1)} aria-label="Receta siguiente">Siguiente</button></div> : <button className="carousel-pause recipe-pause" type="button" onClick={() => setPaused(!paused)}>{paused ? 'Reproducir' : 'Pausar'} recetas</button>}
      </div>
    </section>
  )
}

function Farm() {
  return (
    <section className="farm section-pad" id="nosotros" aria-labelledby="farm-title"><div className="container-fluid"><div className="row g-4 g-lg-5 align-items-center">
      <div className="col-lg-6"><div className="farm-photo-wrap"><img src="/images/farm-hens.png" alt="Gallina en un entorno de campo" /></div></div>
      <div className="col-lg-6 farm-copy"><p className="eyebrow">De nuestra familia a tu mesa</p><h2 id="farm-title">NUESTRA<br />GRANJA<span>.</span></h2><p>Cáscara nace en el campo de nuestra familia, en Carlos Casares, provincia de Buenos Aires.</p><p>Entre mañanas de campo, gallinas y mucho trabajo familiar, aprendimos que las cosas más lindas son las que se hacen con dedicación.</p><p>Para nosotros, cada huevo representa un pedacito de nuestra historia, nuestras raíces y el cariño que ponemos en lo que hacemos.</p><p><strong>Porque Cáscara no es solamente vender huevos. Es compartir un poquito de nuestro campo con cada familia que nos elige.</strong></p><a className="text-link" href="#contacto">HOLA, SOMOS CÁSCARA <Icon name="arrow" /></a></div>
    </div></div></section>
  )
}

function Location() {
  return <section className="location section-pad" aria-labelledby="location-title"><div className="container-fluid"><div className="row g-4 g-lg-5 align-items-center"><div className="col-lg-5"><p className="eyebrow">Nuestro lugar en el mundo</p><h2 id="location-title">NUESTRAS RAÍCES ESTÁN EN CARLOS CASARES</h2><p className="location-place">Provincia de Buenos Aires, Argentina.</p><p className="location-quote">«Nuestras raíces están en el campo. Y queremos que un poquito de él llegue a tu mesa.»</p></div><div className="col-lg-7"><iframe title="Mapa de Carlos Casares, provincia de Buenos Aires, Argentina" src="https://maps.google.com/maps?q=Carlos%20Casares%2C%20Buenos%20Aires%2C%20Argentina&output=embed" loading="lazy" referrerPolicy="no-referrer-when-downgrade" allowFullScreen></iframe><p className="location-caption">Ubicación general de Carlos Casares · <a href="https://www.google.com/maps/search/?api=1&query=Carlos+Casares%2C+Buenos+Aires%2C+Argentina" target="_blank" rel="noreferrer">Abrir mapa en Google Maps</a></p></div></div></div></section>
}

function Footer() {
  const whatsappUrl = /^[1-9]\d{7,14}$/.test(WHATSAPP_NUMBER)
    ? `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(WHATSAPP_MESSAGE)}`
    : null

  return (
    <footer id="contacto" className="footer"><div className="container-fluid"><div className="footer-top"><div><p className="eyebrow">Siempre cerca de tu mesa</p><h2>¿NOS<br />ENCONTRAMOS<span>?</span></h2></div><div className="footer-contact"><p>¿Tenés alguna consulta o querés hacer un pedido? ¡Escribinos por WhatsApp!</p>{whatsappUrl ? <a className="whatsapp-button" href={whatsappUrl} target="_blank" rel="noopener noreferrer"><Icon name="whatsapp" /> ESCRIBINOS POR WHATSAPP</a> : <><button className="whatsapp-button" type="button" disabled aria-describedby="whatsapp-status"><Icon name="whatsapp" /> ESCRIBINOS POR WHATSAPP</button><small id="whatsapp-status" className="whatsapp-status">Número pendiente de configuración.</small></>}</div></div>
      <div className="footer-bottom row g-4 align-items-end"><div className="col-md-5"><Brand light /><p>HUEVOS DE CAMPO · HECHOS PARA COMPARTIR</p></div><div className="col-md-4"><nav aria-label="Navegación del pie de página" className="footer-links">{links.map(([label, href]) => <a key={href} href={href}>{label}</a>)}</nav></div><div className="col-md-3 footer-social"><span>REDES SOCIALES</span><small>Próximamente</small></div></div>
      <div className="footer-last"><span>© CÁSCARA · HUEVOS DE CAMPO</span><span>DEL CAMPO A TU CASA, CON AMOR.</span></div>
    </div></footer>
  )
}

function App() {
  return <><a className="skip-link" href="#contenido">Saltar al contenido</a><Navbar /><main id="contenido"><Hero /><Benefits /><IdentityStrip /><Products /><Recipes /><Farm /><Location /></main><Footer /></>
}

export default App
