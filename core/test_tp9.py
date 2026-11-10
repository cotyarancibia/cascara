from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APITestCase

from core.models import Cart, CartItem, Category, EggInventory, Order, OrderItem, Product, Stock


class ComercioCompartidoTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.cliente = User.objects.create_user('cliente_tp9', email='cliente_tp9@example.test')
        cls.otro = User.objects.create_user('otro_tp9', email='otro_tp9@example.test')
        cls.admin = User.objects.create_user('admin_tp9', role='ADMIN')
        cls.vendedor = User.objects.create_user('vendedor_tp9', role='VENDEDOR')
        cls.categoria = Category.objects.create(nombre='Huevos')
        cls.seis = Product.objects.create(nombre='Seis', categoria=cls.categoria, precio='50.00', huevos_por_unidad=6)
        cls.doce = Product.objects.create(nombre='Doce', categoria=cls.categoria, precio='90.00', huevos_por_unidad=12)
        cls.treinta = Product.objects.create(nombre='Treinta', categoria=cls.categoria, precio='200.00', huevos_por_unidad=30)
        cls.legacy = Product.objects.create(nombre='Histórico', categoria=cls.categoria, precio='1.00')
        cls.legacy_stock = Stock.objects.create(producto=cls.legacy, cantidad=17)
        cls.inventory = EggInventory.objects.create(cantidad=20)
        cls.cart = Cart.objects.create(usuario=cls.cliente)

    def setUp(self):
        self.client.force_authenticate(self.cliente)

    def confirmar(self):
        return self.client.post(f'/api/carritos/{self.cart.pk}/confirmar/', {'direccion_entrega': 'Calle 123', 'total': '0.01'}, format='json')

    def test_presentaciones_disponibilidad_y_busqueda(self):
        data = self.client.get('/api/productos/').data
        available = {item['id']: item['unidades_disponibles'] for item in data}
        self.assertEqual([available[p.pk] for p in (self.seis, self.doce, self.treinta, self.legacy)], [3, 1, 0, 0])
        self.assertEqual(len(self.client.get('/api/productos/?search=Treinta').data), 1)
        self.assertEqual(len(self.client.get(f'/api/productos/?categoria={self.categoria.pk}').data), 4)

    def test_filtros_ids_invalidos_no_provocan_error(self):
        order = Order.objects.create(usuario=self.cliente, direccion_entrega='Calle')
        OrderItem.objects.create(pedido=order, producto=self.seis, cantidad=1, precio_unitario=self.seis.precio)
        self.assertEqual(len(self.client.get('/api/items-pedido/', {'pedido': order.pk}).data), 1)
        for value in ('9' * 5000, '9223372036854775808', '-1', 'abc', ''):
            for url, key in (('/api/productos/', 'categoria'), ('/api/items-pedido/', 'pedido')):
                with self.subTest(value=value[:20], url=url):
                    response = self.client.get(url, {key: value})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.data, [])

    def test_compra_compartida_multiplos_y_precio_servidor(self):
        CartItem.objects.create(carrito=self.cart, producto=self.seis, cantidad=1)
        CartItem.objects.create(carrito=self.cart, producto=self.doce, cantidad=1)
        response = self.confirmar()
        self.assertEqual(response.status_code, 201, response.data)
        self.inventory.refresh_from_db()
        self.legacy_stock.refresh_from_db()
        self.assertEqual((self.inventory.cantidad, self.legacy_stock.cantidad), (2, 17))
        order = Order.objects.get(pk=response.data['id'])
        self.assertEqual((order.total, order.huevos_descontados), (Decimal('140.00'), 18))
        self.assertEqual(set(order.items.values_list('huevos_por_unidad', flat=True)), {6, 12})
        self.assertEqual(len(response.data['items']), 2)
        self.assertFalse(self.cart.items.exists())
        self.assertEqual(self.confirmar().status_code, 400)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.cantidad, 2)

    def test_insuficiente_preserva_datos(self):
        CartItem.objects.create(carrito=self.cart, producto=self.treinta, cantidad=1)
        response = self.confirmar()
        self.assertEqual(response.status_code, 400)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.cantidad, 20)
        self.assertEqual(self.cart.items.count(), 1)
        self.assertFalse(Order.objects.exists())

    def test_carrito_y_pedidos_incluyen_datos_reales(self):
        CartItem.objects.create(carrito=self.cart, producto=self.seis, cantidad=2)
        carrito = self.client.get(f'/api/carritos/{self.cart.pk}/').data
        self.assertEqual(carrito['subtotal_actual'], '100.00')
        self.assertEqual(carrito['items'][0]['producto_detalle']['id'], self.seis.pk)
        order_id = self.confirmar().data['id']
        order = self.client.get(f'/api/pedidos/{order_id}/').data
        self.assertEqual(order['items'][0]['huevos_por_unidad'], 6)
        self.assertEqual(len(self.client.get(f'/api/items-pedido/?pedido={order_id}').data), 1)

    def test_agregar_producto_acumula_en_un_unico_item_propio(self):
        url = '/api/items-carrito/agregar/'
        first = self.client.post(url, {'producto': self.seis.pk, 'cantidad': 1}, format='json')
        self.assertEqual(first.status_code, 201, first.data)
        second = self.client.post(url, {'producto': self.seis.pk, 'cantidad': 2}, format='json')
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(second.data['cantidad'], 3)
        self.assertEqual(self.cart.items.filter(producto=self.seis).count(), 1)
        self.assertEqual(self.client.post(url, {'producto': self.seis.pk, 'cantidad': 0}, format='json').status_code, 400)
        self.client.force_authenticate(self.vendedor)
        self.assertEqual(self.client.post(url, {'producto': self.seis.pk, 'cantidad': 1}, format='json').status_code, 403)
        self.assertEqual(self.cart.items.get(producto=self.seis).cantidad, 3)

    def test_total_excesivo_se_rechaza_sin_modificar_stock(self):
        self.seis.precio = Decimal('99999999.99')
        self.seis.save(update_fields=['precio'])
        CartItem.objects.create(carrito=self.cart, producto=self.seis, cantidad=2)
        self.assertEqual(self.confirmar().status_code, 400)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.cantidad, 20)
        self.assertEqual(self.cart.items.count(), 1)
        self.assertFalse(Order.objects.exists())

    def test_limite_total_items_pendientes_y_rollback(self):
        self.seis.precio = Decimal('99999999.99')
        self.seis.save(update_fields=['precio'])
        order = Order.objects.create(usuario=self.cliente, direccion_entrega='Calle')
        url = '/api/items-pedido/'
        created = self.client.post(url, {'pedido': order.pk, 'producto': self.seis.pk, 'cantidad': 1}, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(self.client.get(f'/api/pedidos/{order.pk}/').data['total'], '99999999.99')
        response = self.client.patch(f"{url}{created.data['id']}/", {'cantidad': 2}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        response = self.client.post(url, {'pedido': order.pk, 'producto': self.doce.pk, 'cantidad': 1}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        order.refresh_from_db()
        self.assertEqual(order.total, Decimal('99999999.99'))
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.get().cantidad, 1)

    def test_cada_presentacion_descuenta_sus_huevos(self):
        for product, expected in ((self.seis, 24), (self.doce, 18), (self.treinta, 0)):
            with self.subTest(product=product.pk):
                self.inventory.cantidad = 30
                self.inventory.save(update_fields=['cantidad'])
                CartItem.objects.create(carrito=self.cart, producto=product, cantidad=1)
                self.assertEqual(self.confirmar().status_code, 201)
                self.inventory.refresh_from_db()
                self.assertEqual(self.inventory.cantidad, expected)

    def test_sin_configuracion_legacy_no_se_adivina(self):
        CartItem.objects.create(carrito=self.cart, producto=self.legacy, cantidad=1)
        self.assertEqual(self.confirmar().status_code, 400)
        self.legacy_stock.refresh_from_db()
        self.assertEqual(self.legacy_stock.cantidad, 17)

    def test_cancelacion_restituye_una_sola_vez_y_conserva_snapshot(self):
        CartItem.objects.create(carrito=self.cart, producto=self.doce, cantidad=1)
        order_id = self.confirmar().data['id']
        self.doce.huevos_por_unidad = 30
        self.doce.save(update_fields=['huevos_por_unidad'])
        self.client.force_authenticate(self.admin)
        url = f'/api/pedidos/{order_id}/'
        self.assertEqual(self.client.patch(url, {'estado': 'CANCELADO'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(url, {'estado': 'CANCELADO'}, format='json').status_code, 200)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.cantidad, 20)
        self.assertEqual(self.client.patch(url, {'estado': 'ENTREGADO'}, format='json').status_code, 400)

    def test_nombre_historico_de_pedido_no_cambia_al_renombrar_producto(self):
        CartItem.objects.create(carrito=self.cart, producto=self.doce, cantidad=1)
        order_id = self.confirmar().data['id']
        self.doce.nombre = 'Otro nombre'
        self.doce.save(update_fields=['nombre'])
        response = self.client.get(f'/api/pedidos/{order_id}/')
        self.assertEqual(response.data['items'][0]['producto_nombre'], 'Doce')

    def test_pedido_historico_no_restituye_automaticamente(self):
        order = Order.objects.create(usuario=self.cliente, estado='CONFIRMADO', direccion_entrega='Calle')
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f'/api/pedidos/{order.pk}/', {'estado': 'CANCELADO'}, format='json').status_code, 400)
        order.refresh_from_db()
        self.inventory.refresh_from_db()
        self.assertEqual((order.estado, self.inventory.cantidad), ('CONFIRMADO', 20))

    def test_transiciones_y_edicion_de_confirmados(self):
        pending = Order.objects.create(usuario=self.cliente, direccion_entrega='Calle')
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f'/api/pedidos/{pending.pk}/', {'estado': 'ENTREGADO'}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/pedidos/', {'estado': 'ENTREGADO', 'direccion_entrega': 'Calle'}, format='json').status_code, 400)
        self.client.force_authenticate(self.cliente)
        CartItem.objects.create(carrito=self.cart, producto=self.seis, cantidad=1)
        order_id = self.confirmar().data['id']
        self.assertEqual(self.client.patch(f'/api/pedidos/{order_id}/', {'direccion_entrega': 'Otra'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(f'/api/pedidos/{order_id}/', {'estado': 'CANCELADO'}, format='json').status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f'/api/pedidos/{order_id}/', {'estado': 'ENTREGADO'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(f'/api/pedidos/{order_id}/', {'estado': 'CANCELADO'}, format='json').status_code, 400)

    def test_reserva_solo_administracion_y_sin_borrado(self):
        self.assertEqual(self.client.put('/api/inventario-huevos/', {'cantidad': 100}, format='json').status_code, 403)
        for user in (self.admin, self.vendedor):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.put('/api/inventario-huevos/', {'cantidad': 20}, format='json').status_code, 200)
            self.assertEqual(self.client.delete('/api/inventario-huevos/').status_code, 405)

    def test_acceso_a_pedido_ajeno(self):
        order = Order.objects.create(usuario=self.otro, direccion_entrega='Calle')
        self.assertEqual(self.client.get(f'/api/pedidos/{order.pk}/').status_code, 403)
        self.assertEqual(self.client.patch(f'/api/pedidos/{order.pk}/', {'direccion_entrega': 'Otra'}, format='json').status_code, 403)

    def test_no_borrar_producto_referenciado_por_pedido(self):
        order = Order.objects.create(usuario=self.cliente, direccion_entrega='Calle')
        OrderItem.objects.create(pedido=order, producto=self.seis, cantidad=1, precio_unitario=self.seis.precio)
        self.client.force_authenticate(self.admin)
        response = self.client.delete(f'/api/productos/{self.seis.pk}/')
        self.assertEqual(response.status_code, 409, response.data)
        self.assertTrue(Product.objects.filter(pk=self.seis.pk).exists())
        self.assertEqual(order.items.count(), 1)

    def test_no_borrar_producto_en_carrito(self):
        CartItem.objects.create(carrito=self.cart, producto=self.seis, cantidad=1)
        self.client.force_authenticate(self.vendedor)
        response = self.client.delete(f'/api/productos/{self.seis.pk}/')
        self.assertEqual(response.status_code, 409, response.data)
        self.assertTrue(Product.objects.filter(pk=self.seis.pk).exists())
        self.assertEqual(self.cart.items.count(), 1)

    def test_edicion_de_perfil_segura_y_correo_duplicado(self):
        url = '/api/auth/profile/'
        self.assertEqual(self.client.patch(url, {'telefono': '123456', 'direccion': 'Calle'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(url, {'role': 'ADMIN'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'email': 'OTRO_TP9@example.test'}, format='json').status_code, 400)
        self.cliente.refresh_from_db()
        self.assertEqual((self.cliente.role, self.cliente.telefono), ('CLIENTE', '123456'))

    def test_capacidades_por_rol_y_superusuario_no_editables(self):
        superuser = get_user_model().objects.create_superuser('super_legacy', 'super@example.test', 'password', role='CLIENTE')
        for user, products, orders in ((self.cliente, False, False), (self.vendedor, True, False), (self.admin, True, True), (superuser, True, True)):
            with self.subTest(user=user.username):
                self.client.force_authenticate(user)
                response = self.client.get('/api/auth/profile/')
                self.assertEqual(response.data['capacidades'], {'gestionar_productos': products, 'gestionar_pedidos': orders})
                self.assertEqual(self.client.patch('/api/auth/profile/', {'capacidades': {'gestionar_pedidos': True}}, format='json').status_code, 400)

    def test_admin_no_edita_ordenes_directamente(self):
        order_admin = admin.site._registry[Order]
        item_admin = admin.site._registry[OrderItem]
        request = type('Request', (), {'user': self.admin})()
        for model_admin in (order_admin, item_admin):
            self.assertFalse(model_admin.has_add_permission(request))
            self.assertFalse(model_admin.has_change_permission(request))
            self.assertFalse(model_admin.has_delete_permission(request))


class ImagenProductoTests(APITestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.media.name, ALLOWED_HOSTS=['testserver'])
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.admin = get_user_model().objects.create_user('admin_imagen', role='ADMIN')
        self.cliente = get_user_model().objects.create_user('cliente_imagen')
        self.categoria = Category.objects.create(nombre='Fotos')

    def image(self, name='producto.png', content_type='image/png', padding=b''):
        output = BytesIO()
        Image.new('RGB', (2, 2), 'red').save(output, format='PNG')
        return SimpleUploadedFile(name, output.getvalue() + padding, content_type=content_type)

    def test_carga_autorizada_url_y_producto_sin_imagen(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/productos/', {'nombre': 'Foto', 'categoria': self.categoria.pk, 'precio': '20.00', 'huevos_por_unidad': '', 'disponible': 'true', 'imagen': self.image()}, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data['disponible'])
        self.assertIn('/media/productos/', response.data['imagen_url'])
        detail = self.client.get(f"/api/productos/{response.data['id']}/")
        self.assertEqual(detail.data['imagen_url'], response.data['imagen_url'])
        self.assertIn(response.data['imagen_url'], [p['imagen_url'] for p in self.client.get('/api/productos/').data])
        blank = self.client.post('/api/productos/', {'nombre': 'Sin foto', 'categoria': self.categoria.pk, 'precio': '20.00'}, format='json')
        self.assertEqual(blank.status_code, 201, blank.data)
        self.assertIsNone(blank.data['imagen_url'])
        updated = self.client.patch(f"/api/productos/{blank.data['id']}/", {'imagen': self.image()}, format='multipart')
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertIn('/media/productos/', updated.data['imagen_url'])
        self.client.force_authenticate(self.cliente)
        rejected = self.client.patch(f"/api/productos/{blank.data['id']}/", {'imagen': self.image()}, format='multipart')
        self.assertEqual(rejected.status_code, 403)
        photo = Product.objects.get(pk=blank.data['id']).imagen
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(f"/api/productos/{blank.data['id']}/").status_code, 204)
        self.assertTrue(photo.storage.exists(photo.name))

    def test_cliente_y_archivos_invalidos_rechazados(self):
        data = {'nombre': 'Foto', 'categoria': self.categoria.pk, 'precio': '20.00', 'imagen': self.image()}
        self.client.force_authenticate(self.cliente)
        self.assertEqual(self.client.post('/api/productos/', data, format='multipart').status_code, 403)
        self.client.force_authenticate(self.admin)
        for image in (self.image(name='falso.jpg'), self.image(content_type='image/jpeg'), self.image(padding=b'x' * (5 * 1024 * 1024)), SimpleUploadedFile('falso.png', b'no es imagen', content_type='image/png')):
            with self.subTest(name=image.name, size=image.size):
                response = self.client.post('/api/productos/', {'nombre': 'Foto', 'categoria': self.categoria.pk, 'precio': '20.00', 'imagen': image}, format='multipart')
                self.assertEqual(response.status_code, 400, response.data)
