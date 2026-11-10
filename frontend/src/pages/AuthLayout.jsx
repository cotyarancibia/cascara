import { Link } from 'react-router-dom'

export default function AuthLayout({ title, intro, children }) {
  return <main className="auth-page">
    <div className="auth-shell container-fluid">
      <div className="row g-0 auth-card">
        <section className="col-lg-6 auth-content" aria-labelledby="auth-title">
          <Link className="brand auth-brand" to="/login" aria-label="Cáscara, ir al inicio de sesión">cás<span className="brand-crack">c</span>ara<span>.</span></Link>
          <p className="auth-eyebrow">Del campo a tu casa</p>
          <h1 id="auth-title">{title}<span>.</span></h1>
          <p className="auth-intro">{intro}</p>
          {children}
        </section>
        <div className="col-lg-6 auth-photo" aria-hidden="true"><img src="/images/farm-hens.png" alt="" /><p>UN POQUITO DE CAMPO,<br />TODOS LOS DÍAS<span>.</span></p></div>
      </div>
    </div>
  </main>
}
