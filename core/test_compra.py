from decimal import Decimal
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Barrier, Event

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from rest_framework.test import APIClient, APITestCase

from core.admin import OrderAdminForm
from core.views import actualizar_total_pedido
from core.models import Cart, CartItem, Category, EggInventory, Order, OrderItem, Product, Stock


class ConfirmarCompraTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('cliente')
        cls.other = get_user_model().objects.create_user('otro')
        cls.admin = get_user_model().objects.create_user('admin', role='ADMIN')
        cls.cart = Cart.objects.create(usuario=cls.user)
        cls.other_cart = Cart.objects.create(usuario=cls.other)
        category = Category.objects.create(nombre='Huevos')
        cls.product = Product.objects.create(nombre='Docena', precio='100.00', categoria=category, huevos_por_unidad=12)
        cls.stock = EggInventory.objects.create(cantidad=25)

    def setUp(self):
        self.client.force_authenticate(self.user)

    def confirmar(self, cart=None, data=None):
        return self.client.post(f'/api/carritos/{(cart or self.cart).pk}/confirmar/',
                                data if data is not None else {'direccion_entrega': 'Calle 123'}, format='json')

    def test_compra_y_reintento(self):
        CartItem.objects.create(carrito=self.cart, producto=self.product, cantidad=2)
        response = self.confirmar(data={'direccion_entrega': 'Calle 123', 'total': '0.01'})
        self.assertEqual(response.status_code, 201)
        pedido = Order.objects.get(pk=response.data['id'])
        item = pedido.items.get()
        self.assertEqual((pedido.usuario, pedido.estado, pedido.total), (self.user, Order.Estado.CONFIRMADO, Decimal('200')))
        self.assertEqual((item.cantidad, item.precio_unitario), (2, Decimal('100')))
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.cantidad, 1)
        self.assertFalse(self.cart.items.exists())
        self.assertEqual(self.confirmar().status_code, 400)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.cantidad, 1)
        self.assertEqual(Order.objects.count(), 1)

    def test_vacio(self):
        self.assertEqual(self.confirmar().status_code, 400)
        self.assertFalse(Order.objects.exists())
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.cantidad, 25)

    def test_insuficiente_no_cambia_datos(self):
        item = CartItem.objects.create(carrito=self.cart, producto=self.product, cantidad=30)
        self.assertEqual(self.confirmar().status_code, 400)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.cantidad, 25)
        self.assertTrue(CartItem.objects.filter(pk=item.pk).exists())
        self.assertFalse(Order.objects.exists())

    def test_varios_productos_uno_insuficiente_no_descontar_ninguno(self):
        category = self.product.categoria
        other = Product.objects.create(nombre='Otra docena', precio='50', categoria=category, huevos_por_unidad=12)
        CartItem.objects.create(carrito=self.cart, producto=self.product, cantidad=2)
        CartItem.objects.create(carrito=self.cart, producto=other, cantidad=2)
        self.assertEqual(self.confirmar().status_code, 400)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.cantidad, 25)
        self.assertEqual(self.cart.items.count(), 2)
        self.assertFalse(Order.objects.exists())

    def test_sin_stock_y_no_disponible(self):
        CartItem.objects.create(carrito=self.cart, producto=self.product, cantidad=1)
        self.stock.delete()
        self.assertEqual(self.confirmar().status_code, 400)
        EggInventory.objects.create(cantidad=25)
        Product.objects.filter(pk=self.product.pk).update(disponible=False)
        self.assertEqual(self.confirmar().status_code, 400)
        self.assertFalse(Order.objects.exists())
        self.assertTrue(self.cart.items.exists())

    def test_ajeno_sin_token_y_rol_incorrecto(self):
        self.assertEqual(self.confirmar(self.other_cart).status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.confirmar().status_code, 401)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.confirmar().status_code, 403)

    def test_direccion_requerida(self):
        CartItem.objects.create(carrito=self.cart, producto=self.product, cantidad=1)
        self.assertEqual(self.confirmar(data={}).status_code, 400)
        self.assertTrue(self.cart.items.exists())
        self.assertFalse(Order.objects.exists())

    def test_error_en_recalculo_revierte_todo(self):
        CartItem.objects.create(carrito=self.cart, producto=self.product, cantidad=2)
        with patch('core.views.actualizar_total_pedido', side_effect=RuntimeError('error')):
            with self.assertRaises(RuntimeError):
                self.confirmar()
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.cantidad, 25)
        self.assertTrue(self.cart.items.exists())
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderItem.objects.exists())

    def test_admin_no_confirma_por_ruta_pedidos(self):
        pedido = Order.objects.create(usuario=self.user, direccion_entrega='Calle')
        self.client.force_authenticate(self.admin)
        data = {'estado': 'CONFIRMADO'}
        self.assertEqual(self.client.patch(f'/api/pedidos/{pedido.pk}/', data, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/pedidos/', {'estado': 'CONFIRMADO', 'direccion_entrega': 'Calle'}, format='json').status_code, 400)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Order.Estado.PENDIENTE)


class AdminOrderFormTests(TestCase):
    def test_admin_no_confirma_directamente(self):
        user = get_user_model().objects.create_user('cliente')
        pedido = Order.objects.create(usuario=user, direccion_entrega='Calle')
        form = OrderAdminForm(instance=pedido, data={'usuario': user.pk, 'estado': 'CONFIRMADO', 'total': '0', 'direccion_entrega': 'Calle'})
        self.assertFalse(form.is_valid())
        self.assertIn('estado', form.errors)


@skipUnlessDBFeature('has_select_for_update')
class CompraConcurrenteTests(TransactionTestCase):
    def test_eliminar_producto_durante_checkout_preserva_pedido_y_stock(self):
        user = get_user_model().objects.create_user('cliente_eliminar')
        admin = get_user_model().objects.create_user('admin_eliminar', role='ADMIN')
        cart = Cart.objects.create(usuario=user)
        category = Category.objects.create(nombre='Huevos')
        product = Product.objects.create(nombre='Seis', precio='10', categoria=category, huevos_por_unidad=6)
        inventory = EggInventory.objects.create(cantidad=20)
        CartItem.objects.create(carrito=cart, producto=product, cantidad=1)
        locked, release = Event(), Event()

        def paused_total(order):
            locked.set()
            if not release.wait(10):
                raise RuntimeError('No se liberó la compra de prueba')
            return actualizar_total_pedido(order)

        def request(user_id, method, path, data=None):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(get_user_model().objects.get(pk=user_id))
                return getattr(client, method)(path, data, format='json').status_code
            finally:
                close_old_connections()

        with patch('core.views.actualizar_total_pedido', side_effect=paused_total):
            with ThreadPoolExecutor(max_workers=2) as executor:
                purchase = executor.submit(request, user.pk, 'post', f'/api/carritos/{cart.pk}/confirmar/', {'direccion_entrega': 'Calle'})
                try:
                    self.assertTrue(locked.wait(10))
                    deletion = executor.submit(request, admin.pk, 'delete', f'/api/productos/{product.pk}/')
                    with self.assertRaises(TimeoutError):
                        deletion.result(timeout=0.5)
                finally:
                    release.set()
                self.assertEqual(purchase.result(timeout=10), 201)
                self.assertEqual(deletion.result(timeout=10), 409)
        inventory.refresh_from_db()
        self.assertEqual(inventory.cantidad, 14)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())
        self.assertEqual(Order.objects.get().items.get().producto_id, product.pk)
        self.assertFalse(cart.items.exists())

    def test_agregados_simultaneos_acumulan_en_un_solo_item(self):
        user = get_user_model().objects.create_user('cliente_agregados')
        cart = Cart.objects.create(usuario=user)
        category = Category.objects.create(nombre='Huevos')
        product = Product.objects.create(nombre='Seis', precio='10', categoria=category, huevos_por_unidad=6)
        CartItem.objects.create(carrito=cart, producto=product, cantidad=1)
        barrier = Barrier(2, timeout=10)

        def agregar(_):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(get_user_model().objects.get(pk=user.pk))
                barrier.wait()
                return client.post('/api/items-carrito/agregar/', {'producto': product.pk, 'cantidad': 1}, format='json').status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(agregar, range(2)))
        self.assertEqual(results, [200, 200])
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.get().cantidad, 3)

    def test_agregado_espera_compra_y_queda_en_carrito_nuevo(self):
        user = get_user_model().objects.create_user('cliente_compra_agregado')
        cart = Cart.objects.create(usuario=user)
        category = Category.objects.create(nombre='Huevos')
        product = Product.objects.create(nombre='Seis', precio='10', categoria=category, huevos_por_unidad=6)
        EggInventory.objects.create(cantidad=60)
        CartItem.objects.create(carrito=cart, producto=product, cantidad=1)
        locked, release = Event(), Event()

        def paused_total(order):
            locked.set()
            if not release.wait(10):
                raise RuntimeError('No se liberó la compra de prueba')
            return actualizar_total_pedido(order)

        def request(path, data):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(get_user_model().objects.get(pk=user.pk))
                return client.post(path, data, format='json').status_code
            finally:
                close_old_connections()

        with patch('core.views.actualizar_total_pedido', side_effect=paused_total):
            with ThreadPoolExecutor(max_workers=2) as executor:
                checkout = executor.submit(request, f'/api/carritos/{cart.pk}/confirmar/', {'direccion_entrega': 'Calle'})
                try:
                    self.assertTrue(locked.wait(10))
                    adding = executor.submit(request, '/api/items-carrito/agregar/', {'producto': product.pk, 'cantidad': 1})
                    with self.assertRaises(TimeoutError):
                        adding.result(timeout=0.5)
                finally:
                    release.set()
                self.assertEqual(checkout.result(timeout=10), 201)
                self.assertEqual(adding.result(timeout=10), 201)
        self.assertEqual(cart.items.get().cantidad, 1)
        self.assertEqual(Order.objects.get().items.get().cantidad, 1)

    def test_dos_confirmaciones_del_mismo_carrito_descuentan_una_vez(self):
        user = get_user_model().objects.create_user('cliente_doble')
        cart = Cart.objects.create(usuario=user)
        category = Category.objects.create(nombre='Huevos')
        product = Product.objects.create(nombre='Seis', precio='10', categoria=category, huevos_por_unidad=6)
        inventory = EggInventory.objects.create(cantidad=20)
        CartItem.objects.create(carrito=cart, producto=product, cantidad=1)
        barrier = Barrier(2, timeout=10)

        def confirmar(_):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(get_user_model().objects.get(pk=user.pk))
                barrier.wait()
                return client.post(f'/api/carritos/{cart.pk}/confirmar/', {'direccion_entrega': 'Calle'}, format='json').status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(confirmar, range(2)))
        self.assertCountEqual(results, [201, 400])
        inventory.refresh_from_db()
        self.assertEqual(inventory.cantidad, 14)
        self.assertEqual(Order.objects.count(), 1)

    def test_cancelaciones_concurrentes_reponen_una_sola_vez(self):
        user = get_user_model().objects.create_user('cliente')
        admin = get_user_model().objects.create_user('admin', role='ADMIN')
        order = Order.objects.create(usuario=user, estado='CONFIRMADO', direccion_entrega='Calle', huevos_descontados=12)
        inventory = EggInventory.objects.create(cantidad=8)
        barrier = Barrier(2, timeout=10)

        def cancelar(_):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(get_user_model().objects.get(pk=admin.pk))
                barrier.wait()
                return client.patch(f'/api/pedidos/{order.pk}/', {'estado': 'CANCELADO'}, format='json').status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(cancelar, range(2)))
        self.assertEqual(results, [200, 200])
        inventory.refresh_from_db()
        self.assertEqual(inventory.cantidad, 20)

    def test_dos_clientes_compiten_por_stock(self):
        category = Category.objects.create(nombre='Huevos')
        products = [Product.objects.create(nombre='Seis', precio='10', categoria=category, huevos_por_unidad=6), Product.objects.create(nombre='Doce', precio='20', categoria=category, huevos_por_unidad=12)]
        stock = EggInventory.objects.create(cantidad=12)
        carts = []
        for name, product in zip(('cliente_a', 'cliente_b'), products):
            user = get_user_model().objects.create_user(name)
            cart = Cart.objects.create(usuario=user)
            CartItem.objects.create(carrito=cart, producto=product, cantidad=1)
            carts.append((user.pk, cart.pk))
        barrier = Barrier(2, timeout=10)

        def comprar(ids):
            close_old_connections()
            try:
                user_id, cart_id = ids
                client = APIClient()
                client.force_authenticate(get_user_model().objects.get(pk=user_id))
                barrier.wait()
                return client.post(f'/api/carritos/{cart_id}/confirmar/',
                                   {'direccion_entrega': 'Calle'}, format='json').status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(comprar, carts))
        self.assertCountEqual(results, [201, 400])
        stock.refresh_from_db()
        self.assertIn(stock.cantidad, (0, 6))
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_editar_item_espera_compra_y_no_recrea_item_eliminado(self):
        user = get_user_model().objects.create_user('cliente')
        cart = Cart.objects.create(usuario=user)
        category = Category.objects.create(nombre='Huevos')
        product = Product.objects.create(nombre='Docena', precio='10', categoria=category, huevos_por_unidad=12)
        EggInventory.objects.create(cantidad=60)
        item = CartItem.objects.create(carrito=cart, producto=product, cantidad=1)
        locked = Event()
        release = Event()

        def paused_total(order):
            locked.set()
            if not release.wait(10):
                raise RuntimeError('No se liberó la compra de prueba')
            return actualizar_total_pedido(order)

        def request(method, path, data):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(get_user_model().objects.get(pk=user.pk))
                return getattr(client, method)(path, data, format='json').status_code
            finally:
                close_old_connections()

        with patch('core.views.actualizar_total_pedido', side_effect=paused_total):
            with ThreadPoolExecutor(max_workers=2) as executor:
                compra = executor.submit(request, 'post', f'/api/carritos/{cart.pk}/confirmar/', {'direccion_entrega': 'Calle'})
                try:
                    self.assertTrue(locked.wait(10))
                    edit = executor.submit(request, 'patch', f'/api/items-carrito/{item.pk}/', {'cantidad': 2})
                    with self.assertRaises(TimeoutError):
                        edit.result(timeout=0.5)
                finally:
                    release.set()
                self.assertEqual(compra.result(timeout=10), 201)
                self.assertEqual(edit.result(timeout=10), 404)
        self.assertFalse(CartItem.objects.filter(pk=item.pk).exists())
