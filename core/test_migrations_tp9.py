from decimal import Decimal

from django.db import connection
from django.db.models.deletion import ProtectedError
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MigracionTP9Tests(TransactionTestCase):
    def test_datos_historicos_no_se_convierten_automaticamente(self):
        executor = MigrationExecutor(connection)
        executor.migrate([('core', '0004_user_user_email_normalized_unique')])
        old = executor.loader.project_state([('core', '0004_user_user_email_normalized_unique')]).apps
        user = old.get_model('core', 'User').objects.create(username='historico')
        category = old.get_model('core', 'Category').objects.create(nombre='Anterior')
        product = old.get_model('core', 'Product').objects.create(nombre='Sin clasificar', categoria=category, precio=Decimal('120.00'))
        old.get_model('core', 'Stock').objects.create(producto=product, cantidad=37)
        order = old.get_model('core', 'Order').objects.create(usuario=user, estado='CONFIRMADO', total=Decimal('120.00'), direccion_entrega='Calle')
        old.get_model('core', 'OrderItem').objects.create(pedido=order, producto=product, cantidad=1, precio_unitario=Decimal('120.00'))

        executor = MigrationExecutor(connection)
        target = ('core', '0005_egginventory_order_huevos_descontados_and_more')
        executor.migrate([target])
        current = executor.loader.project_state([target]).apps
        self.assertIsNone(current.get_model('core', 'Product').objects.get(pk=product.pk).huevos_por_unidad)
        self.assertEqual(current.get_model('core', 'Stock').objects.get(producto_id=product.pk).cantidad, 37)
        self.assertIsNone(current.get_model('core', 'Order').objects.get(pk=order.pk).huevos_descontados)
        self.assertIsNone(current.get_model('core', 'OrderItem').objects.get(pedido_id=order.pk).huevos_por_unidad)
        self.assertFalse(current.get_model('core', 'EggInventory').objects.exists())
        executor = MigrationExecutor(connection)
        target = ('core', '0006_orderitem_nombre_producto_historico_product_imagen')
        executor.migrate([target])
        current = executor.loader.project_state([target]).apps
        self.assertEqual(current.get_model('core', 'Product').objects.get(pk=product.pk).imagen, '')
        self.assertIsNone(current.get_model('core', 'OrderItem').objects.get(pedido_id=order.pk).nombre_producto_historico)
        cart = current.get_model('core', 'Cart').objects.create(usuario_id=user.pk)
        cart_product = current.get_model('core', 'Product').objects.create(nombre='Solo carrito', categoria_id=category.pk, precio=Decimal('20.00'))
        current.get_model('core', 'CartItem').objects.create(carrito_id=cart.pk, producto_id=cart_product.pk, cantidad=2)
        executor = MigrationExecutor(connection)
        target = ('core', '0007_alter_cartitem_producto')
        executor.migrate([target])
        current = executor.loader.project_state([target]).apps
        self.assertEqual(current.get_model('core', 'CartItem').objects.get(carrito_id=cart.pk).cantidad, 2)
        with self.assertRaises(ProtectedError):
            current.get_model('core', 'Product').objects.get(pk=cart_product.pk).delete()

    def tearDown(self):
        MigrationExecutor(connection).migrate([('core', '0007_alter_cartitem_producto')])
        super().tearDown()
