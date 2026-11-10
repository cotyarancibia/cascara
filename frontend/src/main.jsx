import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import 'bootstrap/dist/css/bootstrap.min.css'
import './index.css'
import './auth.css'
import App from './App.jsx'
import { AuthProvider } from './auth/AuthProvider.jsx'
import { ProtectedRoute, GuestRoute } from './auth/Routes.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import { Catalog, ProductDetail } from './store/Catalog.jsx'
import { Cart, Checkout } from './store/Cart.jsx'
import { Orders, Profile } from './store/Account.jsx'
import { AdminInventory, AdminProducts } from './store/Admin.jsx'
import './store.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<App />} />
            <Route path="/productos" element={<Catalog />} />
            <Route path="/productos/:id" element={<ProductDetail />} />
            <Route path="/perfil" element={<Profile />} />
          </Route>
          <Route element={<ProtectedRoute roles={['CLIENTE']} />}>
            <Route path="/carrito" element={<Cart />} />
            <Route path="/checkout" element={<Checkout />} />
            <Route path="/pedidos" element={<Orders />} />
          </Route>
          <Route element={<ProtectedRoute roles={['ADMIN', 'VENDEDOR']} />}>
            <Route path="/admin/productos" element={<AdminProducts />} />
            <Route path="/admin/inventario" element={<AdminInventory />} />
          </Route>
          <Route element={<ProtectedRoute roles={['ADMIN']} />}><Route path="/admin/pedidos" element={<Orders admin />} /></Route>
          <Route element={<GuestRoute />}>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
