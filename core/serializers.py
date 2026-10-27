from rest_framework import serializers
from .models import User, Category, Product, Stock, Cart, CartItem, Order, OrderItem  


# Serializer de categorías
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'nombre', 'descripcion']


# Serializer de productos
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id',
            'nombre',
            'descripcion',
            'precio',
            'categoria',
            'disponible',
            'fecha_creacion'
        ]
        read_only_fields = ['id', 'fecha_creacion']

# Serializer de stock
class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = [
            'id',
            'producto',
            'cantidad',
            'ultima_actualizacion'
        ]
        read_only_fields = ['id', 'ultima_actualizacion']

# Serializer del carrito de compras
class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = [
            'id',
            'usuario',
            'fecha_creacion'
        ]
        read_only_fields = ['id', 'fecha_creacion']


# Serializer de productos dentro del carrito
class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = [
            'id',
            'carrito',
            'producto',
            'cantidad'
        ]
        read_only_fields = ['id']


# Serializer de pedidos
class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            'id',
            'usuario',
            'fecha_pedido',
            'estado',
            'total',
            'direccion_entrega'
        ]
        read_only_fields = ['id', 'fecha_pedido']

# Serializer de los productos de cada pedido
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'pedido',
            'producto',
            'cantidad',
            'precio_unitario'
        ]
        read_only_fields = ['id']
        
# Serializer de usuarios
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'telefono',
            'direccion',
        ]
        read_only_fields = ['id']