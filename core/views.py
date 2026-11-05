from rest_framework import viewsets
from django.db.models import F, Sum, DecimalField, ExpressionWrapper


from .models import (
    Category,
    Product,
    Stock,
    Cart,
    CartItem,
    Order,
    OrderItem,
)

from .serializers import (
    CategorySerializer,
    ProductSerializer,
    StockSerializer,
    CartSerializer,
    CartItemSerializer,
    OrderSerializer,
    OrderItemSerializer,
)


# Vista para las categorías
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


# Vista para los productos
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


# Vista para el stock
class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer


# Vista para los carritos de compras
class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer


# Vista para los productos dentro del carrito
class CartItemViewSet(viewsets.ModelViewSet):
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer


# Vista para los pedidos
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

def actualizar_total_pedido(pedido):
    subtotal = ExpressionWrapper(
        F('cantidad') * F('precio_unitario'),
        output_field=DecimalField(max_digits=12, decimal_places=2)
    )

    total = pedido.items.aggregate(
        total=Sum(subtotal)
    )['total'] or 0

    pedido.total = total
    pedido.save(update_fields=['total'])


# Vista para los productos de cada pedido
class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.select_related('pedido', 'producto')
    serializer_class = OrderItemSerializer

    def perform_create(self, serializer):
        item = serializer.save()
        actualizar_total_pedido(item.pedido)

    def perform_update(self, serializer):
        pedido_anterior = self.get_object().pedido
        item = serializer.save()

        actualizar_total_pedido(item.pedido)

        if pedido_anterior.pk != item.pedido_id:
            actualizar_total_pedido(pedido_anterior)

    def perform_destroy(self, instance):
        pedido = instance.pedido
        instance.delete()
        actualizar_total_pedido(pedido)