"""Pruebas automatizadas de seguridad del TP3 (Identidad, roles y JWT)."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Category, Product, Stock, Cart, Order

User = get_user_model()


class AuthTestCase(APITestCase):
    """Pruebas de registro, login, refresh, perfil y logout."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='Pass1234'
        )
        self.admin.role = User.Role.ADMIN
        self.admin.save()

        self.vendedor = User.objects.create_user(
            username='vendedor', email='v@test.com', password='Pass1234',
            role=User.Role.VENDEDOR,
        )
        self.cliente = User.objects.create_user(
            username='cliente', email='c@test.com', password='Pass1234',
            role=User.Role.CLIENTE,
        )

    def _access_token(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def test_registro_exitoso_cliente(self):
        """1. Registro exitoso de un cliente."""
        data = {
            'username': 'nuevo_cliente',
            'email': 'nuevo@test.com',
            'password': 'ClaveSegura99!',
            'password_confirm': 'ClaveSegura99!',
            'telefono': '123456789',
            'direccion': 'Calle Falsa 123',
        }
        response = self.client.post('/api/auth/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='nuevo_cliente')
        self.assertEqual(user.role, User.Role.CLIENTE)
        self.assertTrue(user.check_password('ClaveSegura99!'))
        self.assertNotIn('password', response.data)
        self.assertNotIn('password_confirm', response.data)

    def test_registro_usuario_duplicado(self):
        """2. Registro con nombre de usuario duplicado."""
        data = {
            'username': 'cliente',
            'email': 'otro@test.com',
            'password': 'Pass1234',
            'password_confirm': 'Pass1234',
        }
        response = self.client.post('/api/auth/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_imposibilidad_registrarse_como_admin(self):
        """3. Imposibilidad de registrarse como administrador."""
        data = {
            'username': 'falso_admin',
            'email': 'falso@test.com',
            'password': 'ClaveSegura99!',
            'password_confirm': 'ClaveSegura99!',
            'role': User.Role.ADMIN,  # el servidor debe ignorarlo
        }
        response = self.client.post('/api/auth/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='falso_admin')
        self.assertEqual(user.role, User.Role.CLIENTE)

    def test_login_exitoso_con_jwt(self):
        """4. Login exitoso con JWT."""
        response = self.client.post(
            '/api/auth/login/',
            {'username': 'cliente', 'password': 'Pass1234'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertNotIn('password', response.data)

    def test_login_credenciales_incorrectas(self):
        """5. Login con credenciales incorrectas."""
        response = self.client.post(
            '/api/auth/login/',
            {'username': 'cliente', 'password': 'contraseña_mala'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_renovacion_de_access_token(self):
        """6. Renovación de access token."""
        login = self.client.post(
            '/api/auth/login/',
            {'username': 'cliente', 'password': 'Pass1234'},
            format='json',
        )
        refresh = login.data['refresh']
        response = self.client.post(
            '/api/auth/refresh/',
            {'refresh': refresh},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_acceso_a_perfil_con_token_valido(self):
        """7. Acceso a perfil con token válido."""
        token = self._access_token(self.cliente)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'cliente')
        self.assertEqual(response.data['role'], User.Role.CLIENTE)
        self.assertNotIn('password', response.data)

    def test_acceso_sin_token_respuesta_401(self):
        """8. Acceso sin token: respuesta 401 Unauthorized."""
        self.client.credentials()
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_y_revocacion_refresh_token(self):
        """15. Logout y revocación del refresh token."""
        token = self._access_token(self.cliente)
        refresh = str(RefreshToken.for_user(self.cliente))
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        response = self.client.post(
            '/api/auth/logout/', {'refresh': refresh}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

        # El refresh token revocado ya no debe poder renovar el access.
        refresh_response = self.client.post(
            '/api/auth/refresh/', {'refresh': refresh}, format='json'
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)


class RolesYPermisosTestCase(APITestCase):
    """Pruebas de autorización basada en roles."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='Pass1234'
        )
        self.admin.role = User.Role.ADMIN
        self.admin.save()

        self.vendedor = User.objects.create_user(
            username='vendedor', email='v@test.com', password='Pass1234',
            role=User.Role.VENDEDOR,
        )
        self.cliente = User.objects.create_user(
            username='cliente', email='c@test.com', password='Pass1234',
            role=User.Role.CLIENTE,
        )
        self.cliente2 = User.objects.create_user(
            username='cliente2', email='c2@test.com', password='Pass1234',
            role=User.Role.CLIENTE,
        )

        self.categoria = Category.objects.create(
            nombre='Huevos', descripcion='Huevos de campo'
        )
        self.producto = Product.objects.create(
            nombre='Docena de huevos',
            descripcion='Docena de huevos de campo',
            precio=1000.00,
            categoria=self.categoria,
            disponible=True,
        )
        self.stock = Stock.objects.create(
            producto=self.producto, cantidad=50
        )

    def _token(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def _authenticate(self, user):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self._token(user))

    def test_cliente_no_puede_crear_productos(self):
        """9. Cliente intentando crear productos: 403 Forbidden."""
        self._authenticate(self.cliente)
        data = {
            'nombre': 'Producto ilegal',
            'precio': 100.00,
            'categoria': self.categoria.id,
        }
        response = self.client.post('/api/productos/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_crea_productos_correctamente(self):
        """10. Administrador creando productos correctamente."""
        self._authenticate(self.admin)
        data = {
            'nombre': 'Producto admin',
            'precio': 200.00,
            'categoria': self.categoria.id,
        }
        response = self.client.post('/api/productos/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_vendedor_crea_productos_correctamente(self):
        """11. Vendedor creando productos correctamente."""
        self._authenticate(self.vendedor)
        data = {
            'nombre': 'Producto vendedor',
            'precio': 300.00,
            'categoria': self.categoria.id,
        }
        response = self.client.post('/api/productos/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cliente_no_accede_a_carrito_ajeno(self):
        """12. Cliente accediendo a un carrito ajeno: acceso denegado."""
        cart_ajeno = Cart.objects.create(usuario=self.cliente2)
        self._authenticate(self.cliente)
        response = self.client.get(
            f'/api/carritos/{cart_ajeno.id}/', format='json'
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )

    def test_cliente_no_consulta_pedido_ajeno(self):
        """13. Cliente intentando consultar un pedido ajeno: acceso denegado."""
        pedido_ajeno = Order.objects.create(
            usuario=self.cliente2,
            estado=Order.Estado.PENDIENTE,
            total=0,
            direccion_entrega='Calle X 123',
        )
        self._authenticate(self.cliente)
        response = self.client.get(
            f'/api/pedidos/{pedido_ajeno.id}/', format='json'
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )

    def test_cliente_no_puede_modificar_stock(self):
        """14. Cliente intentando modificar stock: 403 Forbidden."""
        self._authenticate(self.cliente)
        data = {'cantidad': 999}
        response = self.client.patch(
            f'/api/stock/{self.stock.id}/', data, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_total_pedido_calculado_automaticamente(self):
        """16. Comprobación de que el total de pedidos sigue calculándose."""
        self._authenticate(self.cliente)
        pedido = Order.objects.create(
            usuario=self.cliente,
            estado=Order.Estado.PENDIENTE,
            total=0,
            direccion_entrega='Calle Y 456',
        )
        # Se crea el ítem a través de la API para que pase por
        # OrderItemViewSet.perform_create (cálculo automático del total).
        response = self.client.post(
            '/api/items-pedido/',
            {
                'pedido': pedido.id,
                'producto': self.producto.id,
                'cantidad': 3,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pedido.refresh_from_db()
        self.assertEqual(pedido.total, 3 * self.producto.precio)
