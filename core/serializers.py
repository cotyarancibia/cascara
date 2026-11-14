from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Category, Product, Stock, EggInventory, Cart, CartItem, Order, OrderItem


class ConfirmarCompraSerializer(serializers.Serializer):
    direccion_entrega = serializers.CharField(max_length=255, allow_blank=False)


class AgregarCarritoSerializer(serializers.Serializer):
    producto = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    cantidad = serializers.IntegerField(min_value=1, max_value=2147483647)


# Serializer de categorías
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'nombre', 'descripcion']


# Serializer de productos
class ProductImageField(serializers.ImageField):
    def to_internal_value(self, data):
        declared_type = getattr(data, 'content_type', None)
        image = super().to_internal_value(data)
        if declared_type and declared_type != image.content_type:
            raise serializers.ValidationError('El tipo de archivo no coincide con la imagen.')
        return image


class ProductSerializer(serializers.ModelSerializer):
    unidades_disponibles = serializers.SerializerMethodField()
    imagen = ProductImageField(required=False, allow_null=True, write_only=True)
    imagen_url = serializers.ImageField(source='imagen', read_only=True)

    def validate_imagen(self, value):
        if value:
            from .image_validation import validate_product_image
            validate_product_image(value)
        return value

    def get_unidades_disponibles(self, obj) -> int:
        if not obj.disponible or not obj.huevos_por_unidad:
            return 0
        if 'inventario_huevos' not in self.context:
            self.context['inventario_huevos'] = EggInventory.objects.filter(pk=1).values_list('cantidad', flat=True).first()
        inventory = self.context['inventario_huevos']
        if inventory is None:
            return 0
        return inventory // obj.huevos_por_unidad

    class Meta:
        model = Product
        fields = [
            'id',
            'nombre',
            'descripcion',
            'precio',
            'categoria',
            'disponible',
            'fecha_creacion', 'huevos_por_unidad', 'unidades_disponibles', 'imagen', 'imagen_url'
        ]
        read_only_fields = ['id', 'fecha_creacion']


class EggInventorySerializer(serializers.ModelSerializer):
    cantidad = serializers.IntegerField(min_value=0, max_value=2147483647)
    class Meta:
        model = EggInventory
        fields = ['cantidad', 'ultima_actualizacion']
        read_only_fields = ['ultima_actualizacion']

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
    items = serializers.SerializerMethodField()
    subtotal_actual = serializers.SerializerMethodField()

    @extend_schema_field({'type': 'array', 'items': {'$ref': '#/components/schemas/CartItem'}})
    def get_items(self, obj):
        return CartItemSerializer(obj.items.select_related('producto'), many=True, context=self.context).data

    def get_subtotal_actual(self, obj) -> str:
        total = sum((item.producto.precio * item.cantidad for item in obj.items.select_related('producto')), start=0)
        return format(total, '.2f')

    class Meta:
        model = Cart
        fields = [
            'id',
            'usuario',
            'fecha_creacion', 'items', 'subtotal_actual'
        ]
        read_only_fields = ['id', 'usuario', 'fecha_creacion']


# Serializer de productos dentro del carrito
class CartItemSerializer(serializers.ModelSerializer):
    producto_detalle = ProductSerializer(source='producto', read_only=True)
    class Meta:
        model = CartItem
        fields = [
            'id',
            'carrito',
            'producto',
            'cantidad', 'producto_detalle'
        ]
        read_only_fields = ['id', 'carrito']

    def validate(self, attrs):
        product = attrs.get('producto', getattr(self.instance, 'producto', None))
        user = self.context['request'].user
        matches = CartItem.objects.filter(carrito__usuario=user, producto=product)
        if self.instance:
            matches = matches.exclude(pk=self.instance.pk)
        if matches.exists():
            raise serializers.ValidationError({'producto': 'El producto ya está en el carrito.'})
        return attrs


# Serializer de pedidos
class OrderSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    @extend_schema_field({'type': 'array', 'items': {'$ref': '#/components/schemas/OrderItem'}})
    def get_items(self, obj):
        return OrderItemSerializer(obj.items.select_related('producto'), many=True, context=self.context).data

    class Meta:
        model = Order
        fields = [
            'id',
            'usuario',
            'fecha_pedido',
            'estado',
            'total',
            'direccion_entrega', 'huevos_descontados', 'items'
        ]
        read_only_fields = ['id', 'usuario', 'fecha_pedido', 'total', 'huevos_descontados', 'items']


class OrderContactSerializer(serializers.Serializer):
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    telefono = serializers.CharField(read_only=True, allow_blank=True)


class AdminOrderSerializer(OrderSerializer):
    cliente_contacto = OrderContactSerializer(source='usuario', read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ['cliente_contacto']
        read_only_fields = OrderSerializer.Meta.read_only_fields + ['cliente_contacto']

# Serializer de los productos de cada pedido
class OrderItemSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.SerializerMethodField()

    def get_producto_nombre(self, obj) -> str:
        return obj.nombre_producto_historico or 'Nombre histórico no disponible'
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'pedido',
            'producto',
            'cantidad',
            'precio_unitario', 'huevos_por_unidad', 'producto_nombre'
        ]
        read_only_fields = ['id', 'precio_unitario', 'huevos_por_unidad', 'producto_nombre']

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None:
            fields['pedido'].read_only = True
        return fields
    def create(self, validated_data):
        validated_data['precio_unitario'] = validated_data['producto'].precio
        validated_data['nombre_producto_historico'] = validated_data['producto'].nombre
        return super().create(validated_data)

    def update(self, instance, validated_data):
        producto = validated_data.get('producto')

        if producto is not None and producto.pk != instance.producto_id:
            validated_data['precio_unitario'] = producto.precio
            validated_data['nombre_producto_historico'] = producto.nombre

        return super().update(instance, validated_data)
