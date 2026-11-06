from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Cart, CartItem, Category, Order, OrderItem, Product


class SecurityRegressionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user('alice', password='test')
        cls.other = User.objects.create_user('bob', password='test')
        category = Category.objects.create(nombre='Huevos')
        cls.product = Product.objects.create(nombre='Docena', precio=10, categoria=category)
        cls.cart = Cart.objects.create(usuario=cls.user)
        cls.other_cart = Cart.objects.create(usuario=cls.other)
        cls.cart_item = CartItem.objects.create(carrito=cls.cart, producto=cls.product)
        cls.other_cart_item = CartItem.objects.create(carrito=cls.other_cart, producto=cls.product)
        cls.order = Order.objects.create(usuario=cls.user, direccion_entrega='Calle 1', total=10)
        cls.other_order = Order.objects.create(usuario=cls.other, direccion_entrega='Calle 2', total=10)
        cls.item = OrderItem.objects.create(pedido=cls.order, producto=cls.product, cantidad=1, precio_unitario=10)
        cls.other_item = OrderItem.objects.create(pedido=cls.other_order, producto=cls.product, cantidad=1, precio_unitario=10)

    def setUp(self):
        self.client.force_authenticate(self.user)

    def test_propietarios_y_relaciones_inmutables(self):
        tercero = get_user_model().objects.create_user('tercero', password='test')
        cases = [
            (f'/api/carritos/{self.cart.pk}/', {'usuario': tercero.pk}, self.cart, 'usuario_id', self.user.pk),
            (f'/api/pedidos/{self.order.pk}/', {'usuario': self.other.pk}, self.order, 'usuario_id', self.user.pk),
            (f'/api/items-carrito/{self.cart_item.pk}/', {'carrito': self.other_cart.pk}, self.cart_item, 'carrito_id', self.cart.pk),
            (f'/api/items-pedido/{self.item.pk}/', {'pedido': self.other_order.pk}, self.item, 'pedido_id', self.order.pk),
        ]
        for url, data, instance, attr, expected in cases:
            with self.subTest(url=url):
                self.client.patch(url, data, format='json')
                instance.refresh_from_db()
                self.assertEqual(getattr(instance, attr), expected)

    def test_items_propios_y_ajenos(self):
        for own, other, endpoint in [(self.cart_item, self.other_cart_item, 'items-carrito'), (self.item, self.other_item, 'items-pedido')]:
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.client.get(f'/api/{endpoint}/{own.pk}/').status_code, 200)
                self.assertEqual(self.client.patch(f'/api/{endpoint}/{own.pk}/', {'cantidad': 2}, format='json').status_code, 200)
                for method in (self.client.get, self.client.patch, self.client.delete):
                    self.assertIn(method(f'/api/{endpoint}/{other.pk}/').status_code, (403, 404))

    def test_pedido_nuevo_no_admite_estado_privilegiado(self):
        response = self.client.post('/api/pedidos/', {'direccion_entrega': 'Calle 3', 'estado': 'ENTREGADO'}, format='json')
        self.assertIn(response.status_code, (201, 400, 403))
        if response.status_code == 201:
            self.assertEqual(Order.objects.get(pk=response.data['id']).estado, Order.Estado.PENDIENTE)

    def test_pedidos_cerrados_no_admiten_cambios_de_items(self):
        for state in ('CONFIRMADO', 'ENTREGADO', 'CANCELADO'):
            with self.subTest(state=state):
                Order.objects.filter(pk=self.order.pk).update(estado=state)
                self.assertIn(self.client.post('/api/items-pedido/', {'pedido': self.order.pk, 'producto': self.product.pk, 'cantidad': 2}, format='json').status_code, (400, 403))
                self.assertIn(self.client.patch(f'/api/items-pedido/{self.item.pk}/', {'cantidad': 2}, format='json').status_code, (400, 403))
                self.assertIn(self.client.delete(f'/api/items-pedido/{self.item.pk}/').status_code, (400, 403))
                self.assertIn(self.client.delete(f'/api/pedidos/{self.order.pk}/').status_code, (400, 403))
                self.order.refresh_from_db()
                self.item.refresh_from_db()
                self.assertEqual(self.order.total, Decimal('10'))
                self.assertEqual(self.item.cantidad, 1)

    def test_fallo_recalculo_revierte_item(self):
        with patch('core.views.actualizar_total_pedido', side_effect=RuntimeError('fallo')):
            with self.assertRaises(RuntimeError):
                self.client.post('/api/items-pedido/', {'pedido': self.order.pk, 'producto': self.product.pk, 'cantidad': 2}, format='json')
        self.assertEqual(OrderItem.objects.filter(pedido=self.order).count(), 1)
        self.order.refresh_from_db()
        self.assertEqual(self.order.total, Decimal('10'))

    def test_fallo_recalculo_revierte_modificacion_y_borrado(self):
        for method, data in ((self.client.patch, {'cantidad': 5}), (self.client.delete, None)):
            with self.subTest(method=method.__name__):
                with patch('core.views.actualizar_total_pedido', side_effect=RuntimeError('fallo')):
                    with self.assertRaises(RuntimeError):
                        method(f'/api/items-pedido/{self.item.pk}/', data, format='json')
                self.item.refresh_from_db()
                self.order.refresh_from_db()
                self.assertEqual(self.item.cantidad, 1)
                self.assertEqual(self.order.total, Decimal('10'))

    def test_creacion_y_unicidad_carrito(self):
        response = self.client.post('/api/carritos/', {}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['usuario'], self.user.pk)
        response = self.client.post('/api/items-carrito/', {'producto': self.product.pk}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_crear_y_eliminar_items_propios(self):
        self.cart_item.delete()
        response = self.client.post('/api/items-carrito/', {'producto': self.product.pk, 'carrito': self.other_cart.pk}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['carrito'], self.cart.pk)
        self.assertEqual(self.client.delete(f"/api/items-carrito/{response.data['id']}/").status_code, 204)
        response = self.client.post('/api/items-pedido/', {'pedido': self.order.pk, 'producto': self.product.pk, 'cantidad': 2}, format='json')
        self.assertEqual(response.status_code, 201)
        self.order.refresh_from_db()
        self.assertEqual(self.order.total, Decimal('30'))
        self.assertEqual(self.client.delete(f"/api/items-pedido/{response.data['id']}/").status_code, 204)
        self.order.refresh_from_db()
        self.assertEqual(self.order.total, Decimal('10'))

    def test_no_crea_item_en_pedido_ajeno(self):
        response = self.client.post('/api/items-pedido/', {'pedido': self.other_order.pk, 'producto': self.product.pk, 'cantidad': 1}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(OrderItem.objects.filter(pedido=self.other_order).count(), 1)

    def test_password_similar_rechazada(self):
        self.client.force_authenticate(None)
        response = self.client.post('/api/auth/register/', {'username': 'nombresimilar', 'email': 'otro@example.com', 'password': 'nombresimilar', 'password_confirm': 'nombresimilar'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_logout_no_revoca_token_ajeno(self):
        token = str(RefreshToken.for_user(self.other))
        response = self.client.post('/api/auth/logout/', {'refresh': token}, format='json')
        self.assertIn(response.status_code, (400, 403))
        self.assertEqual(self.client.post('/api/auth/refresh/', {'refresh': token}, format='json').status_code, 200)

    def test_superusuario_con_rol_por_defecto_conserva_privilegios(self):
        admin = get_user_model().objects.create_superuser('super', password='test')
        self.client.force_authenticate(admin)
        response = self.client.post('/api/productos/', {'nombre': 'Producto admin', 'precio': '20', 'categoria': self.product.categoria_id}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_staff_no_es_promovido_automaticamente(self):
        staff = get_user_model().objects.create_user('staff', password='test', is_staff=True)
        self.client.force_authenticate(staff)
        response = self.client.post('/api/productos/', {'nombre': 'Producto staff', 'precio': '20', 'categoria': self.product.categoria_id}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(staff.is_staff)
        self.assertEqual(staff.role, get_user_model().Role.CLIENTE)
