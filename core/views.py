from rest_framework import viewsets, permissions, filters, generics
from decimal import Decimal
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from django.db import IntegrityError, transaction
from django.db.models import F, Q, Sum, DecimalField, ExpressionWrapper, Exists, OuterRef
from django.db.models.deletion import ProtectedError

from .models import (
    Category,
    Product,
    Stock,
    EggInventory,
    Cart,
    CartItem,
    Order,
    OrderItem,
)

from .serializers import (
    CategorySerializer,
    ProductSerializer,
    StockSerializer,
    EggInventorySerializer,
    CartSerializer,
    CartItemSerializer,
    OrderSerializer,
    AdminOrderSerializer,
    OrderItemSerializer,
    ConfirmarCompraSerializer,
    AgregarCarritoSerializer,
)

from users.permissions import (
    IsAdmin,
    IsAdminOrVendedor,
    IsCliente,
    IsOwnerOrAdmin,
)


# ----------------------------------------------------------------
# Helper: decidir permisos por acción en cada ViewSet
# ----------------------------------------------------------------

def _role_permissions(read_roles, write_roles):
    """Devuelve una clase de permiso que permite lectura a `read_roles` y
    escritura solo a `write_roles`. read_roles/write_roles son tuplas de
    strings ('ADMIN', 'CLIENTE', 'VENDEDOR') o el valor especial 'ANY'."""
    class _RolePermission(permissions.BasePermission):
        def has_permission(self, request, view):
            user = request.user
            action = getattr(view, 'action', None)
            is_write = action in ('create', 'update', 'partial_update', 'destroy')

            def allowed(roles):
                if 'ANY' in roles:
                    return True
                if not user or not user.is_authenticated:
                    return False
                if user.is_superuser:
                    return True
                return user.role in roles

            return allowed(write_roles) if is_write else allowed(read_roles)

    return _RolePermission


def _filter_pk(value):
    """Parse a positive signed-64-bit key without unbounded integer conversion."""
    if not value or not value.isascii() or not value.isdecimal() or len(value) > 19:
        return None
    pk = int(value)
    return pk if 1 <= pk <= 9223372036854775807 else None


# ----------------------------------------------------------------
# Categorías
# ----------------------------------------------------------------
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [IsAdminOrVendedor]
        return super().get_permissions()


# ----------------------------------------------------------------
# Productos
# ----------------------------------------------------------------
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'descripcion']

    def destroy(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                product = self.get_object()
                product = get_object_or_404(Product.objects.select_for_update(), pk=product.pk)
                if CartItem.objects.filter(producto=product).exists():
                    return Response({'detail': 'No se puede eliminar el producto porque está en un carrito.'}, status=status.HTTP_409_CONFLICT)
                self.perform_destroy(product)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except (ProtectedError, IntegrityError):
            return Response({'detail': 'No se puede eliminar el producto porque está asociado a carritos o pedidos.'}, status=status.HTTP_409_CONFLICT)

    def get_queryset(self):
        queryset = super().get_queryset()
        categoria = self.request.query_params.get('categoria')
        if categoria is not None:
            categoria_id = _filter_pk(categoria)
            queryset = queryset.filter(categoria_id=categoria_id) if categoria_id is not None else queryset.none()
        disponible = self.request.query_params.get('disponible')
        if disponible is not None:
            if disponible.lower() not in ('true', 'false'):
                raise ValidationError({'disponible': 'Use true o false.'})
            inventory = EggInventory.objects.filter(pk=1, cantidad__gte=OuterRef('huevos_por_unidad'))
            queryset = queryset.annotate(reserva_suficiente=Exists(inventory))
            buyable = Q(disponible=True, huevos_por_unidad__gte=1, reserva_suficiente=True)
            queryset = queryset.filter(buyable) if disponible.lower() == 'true' else queryset.exclude(buyable)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['inventario_huevos'] = EggInventory.objects.filter(pk=1).values_list('cantidad', flat=True).first()
        return context

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [IsAdminOrVendedor]
        return super().get_permissions()


# ----------------------------------------------------------------
# Stock
# ----------------------------------------------------------------
class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [IsAdminOrVendedor]
        return super().get_permissions()


class EggInventoryView(generics.GenericAPIView):
    """Reserva común en huevos; configuración explícita, sin crear datos en migraciones."""
    serializer_class = EggInventorySerializer
    def get_permissions(self):
        return [permissions.AllowAny()] if self.request.method == 'GET' else [IsAdminOrVendedor()]

    @extend_schema(responses=EggInventorySerializer)
    def get(self, request):
        return Response(EggInventorySerializer(get_object_or_404(EggInventory, pk=1)).data)

    @transaction.atomic
    @extend_schema(request=EggInventorySerializer, responses=EggInventorySerializer)
    def put(self, request):
        serializer = EggInventorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inventory, _ = EggInventory.objects.get_or_create(pk=1, defaults={'cantidad': serializer.validated_data['cantidad']})
        inventory = EggInventory.objects.select_for_update().get(pk=inventory.pk)
        inventory.cantidad = serializer.validated_data['cantidad']
        inventory.save(update_fields=['cantidad', 'ultima_actualizacion'])
        return Response(EggInventorySerializer(inventory).data)


# ----------------------------------------------------------------
# Carritos (solo CLIENTE gestiona SU carrito)
# ----------------------------------------------------------------
class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsCliente, IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        base = Cart.objects.all()
        # En list, el cliente solo ve su propio carrito. En retrieve se
        # consulta sobre todos para poder devolver 403 (propiedad denegada)
        # en lugar de 404 cuando se accede a un carrito ajeno (evita IDOR).
        if self.action == 'list':
            if user.is_superuser or user.role == 'ADMIN':
                return base
            return base.filter(usuario=user)
        return base

    def perform_create(self, serializer):
        # No confiar en el ID de usuario enviado desde el frontend.
        # El carrito pertenece siempre al usuario autenticado.
        user = self.request.user
        cart, _ = Cart.objects.get_or_create(usuario=user)
        serializer.instance = cart
        serializer.save()

    def get_object(self):
        # Asegura que un cliente solo acceda a su propio carrito.
        obj = super().get_object()
        user = self.request.user
        if not (user.is_superuser or user.role == 'ADMIN') and obj.usuario != user:
            raise PermissionDenied("No tienes acceso a este carrito.")
        return obj

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        carrito = self.get_object()
        get_object_or_404(Cart.objects.select_for_update(), pk=carrito.pk)
        return super().destroy(request, *args, **kwargs)

    @extend_schema(request=ConfirmarCompraSerializer, responses={201: OrderSerializer})
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def confirmar(self, request, pk=None):
        carrito = self.get_object()
        if carrito.usuario_id != request.user.pk:
            raise PermissionDenied('Solo puedes confirmar tu propio carrito.')
        carrito = get_object_or_404(Cart.objects.select_for_update(), pk=carrito.pk)
        datos = ConfirmarCompraSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        items = list(CartItem.objects.filter(carrito=carrito).order_by('producto_id'))
        if not items:
            raise ValidationError({'detail': 'El carrito está vacío.'})

        ids = [item.producto_id for item in items]
        productos = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=ids).order_by('pk')}
        inventory = EggInventory.objects.select_for_update().filter(pk=1).first()
        if inventory is None:
            raise ValidationError({'detail': 'La reserva de huevos todavía no está configurada.'})
        huevos_requeridos = 0
        for item in items:
            producto = productos.get(item.producto_id)
            if producto is None:
                raise ValidationError({'detail': 'Un producto del carrito ya no existe.'})
            if not producto.disponible or not producto.huevos_por_unidad or item.cantidad < 1:
                raise ValidationError({'detail': f'Producto no disponible o sin presentación configurada: {producto.nombre}.'})
            huevos_requeridos += producto.huevos_por_unidad * item.cantidad

        if inventory.cantidad < huevos_requeridos:
            raise ValidationError({'detail': 'Stock insuficiente de huevos para las presentaciones solicitadas.'})
        total = sum((productos[item.producto_id].precio * item.cantidad for item in items), Decimal('0'))
        validar_limite_total(total)

        pedido = Order.objects.create(usuario=request.user, estado=Order.Estado.CONFIRMADO,
                                      direccion_entrega=datos.validated_data['direccion_entrega'], huevos_descontados=huevos_requeridos)
        for item in items:
            producto = productos[item.producto_id]
            OrderItem.objects.create(pedido=pedido, producto=producto,
                                     cantidad=item.cantidad, precio_unitario=producto.precio, huevos_por_unidad=producto.huevos_por_unidad,
                                     nombre_producto_historico=producto.nombre)
        inventory.cantidad -= huevos_requeridos
        inventory.save(update_fields=['cantidad', 'ultima_actualizacion'])
        actualizar_total_pedido(pedido)
        CartItem.objects.filter(carrito=carrito).delete()
        return Response(OrderSerializer(pedido).data, status=status.HTTP_201_CREATED)


# ----------------------------------------------------------------
# Ítems del carrito (misma restricción de propiedad)
# ----------------------------------------------------------------
class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsCliente, IsOwnerOrAdmin]

    @extend_schema(request=AgregarCarritoSerializer, responses={200: CartItemSerializer, 201: CartItemSerializer})
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def agregar(self, request):
        data = AgregarCarritoSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        carrito, _ = Cart.objects.get_or_create(usuario=request.user)
        carrito = Cart.objects.select_for_update().get(pk=carrito.pk)
        producto = get_object_or_404(Product.objects.select_for_update(), pk=data.validated_data['producto'].pk)
        cantidad = data.validated_data['cantidad']
        item = CartItem.objects.filter(carrito=carrito, producto=producto).first()
        if item:
            if item.cantidad + cantidad > 2147483647:
                raise ValidationError({'cantidad': 'La cantidad supera el máximo permitido.'})
            item.cantidad += cantidad
            item.save(update_fields=['cantidad'])
            response_status = status.HTTP_200_OK
        else:
            item = CartItem.objects.create(carrito=carrito, producto=producto, cantidad=cantidad)
            response_status = status.HTTP_201_CREATED
        return Response(self.get_serializer(item).data, status=response_status)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        carrito, _ = Cart.objects.get_or_create(usuario=request.user)
        get_object_or_404(Cart.objects.select_for_update(), pk=carrito.pk)
        return super().create(request, *args, **kwargs)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        item = self.get_object()
        get_object_or_404(Cart.objects.select_for_update(), pk=item.carrito_id)
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        item = self.get_object()
        get_object_or_404(Cart.objects.select_for_update(), pk=item.carrito_id)
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        base = CartItem.objects.all()
        if self.action == 'list':
            if user.is_superuser or user.role == 'ADMIN':
                return base
            return base.filter(carrito__usuario=user)
        return base

    def perform_create(self, serializer):
        user = self.request.user
        carrito, _ = Cart.objects.get_or_create(usuario=user)
        # Asociar siempre al carrito del usuario autenticado, ignorando
        # cualquier carrito enviado desde el frontend.
        try:
            with transaction.atomic():
                producto = get_object_or_404(Product.objects.select_for_update(), pk=serializer.validated_data['producto'].pk)
                serializer.save(carrito=carrito, producto=producto)
        except IntegrityError:
            raise ValidationError({'producto': 'No se pudo agregar el producto al carrito.'})

    def perform_update(self, serializer):
        producto = serializer.validated_data.get('producto')
        if producto is not None:
            producto = get_object_or_404(Product.objects.select_for_update(), pk=producto.pk)
            serializer.save(producto=producto)
        else:
            serializer.save()

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if not (user.is_superuser or user.role == 'ADMIN'):
            if obj.carrito.usuario != user:
                raise PermissionDenied("No tienes acceso a este ítem del carrito.")
        return obj


# ----------------------------------------------------------------
# Pedidos
# ----------------------------------------------------------------
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer

    def get_serializer_class(self):
        user = self.request.user
        if self.action in ('list', 'retrieve') and user.is_authenticated and (user.is_superuser or user.role == 'ADMIN'):
            return AdminOrderSerializer
        return OrderSerializer

    def get_permissions(self):
        if self.action == 'list':
            self.permission_classes = [permissions.IsAuthenticated]
        elif self.action == 'retrieve':
            self.permission_classes = [
                permissions.IsAuthenticated, IsOwnerOrAdmin
            ]
        elif self.action == 'create':
            self.permission_classes = [permissions.IsAuthenticated]
        else:
            # update / destroy son operaciones administrativas o del dueño.
            self.permission_classes = [IsOwnerOrAdmin]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        base = Order.objects.select_related('usuario')
        # En list, el cliente solo ve sus propios pedidos. En retrieve se
        # consulta sobre todos para poder devolver 403 al acceder a un
        # pedido ajeno (evita IDOR).
        if self.action == 'list':
            if user.is_superuser or user.role == 'ADMIN':
                return base
            return base.filter(usuario=user)
        return base

    def perform_create(self, serializer):
        # El pedido pertenece siempre al usuario autenticado.
        user = self.request.user
        if serializer.validated_data.get('estado') == Order.Estado.CONFIRMADO:
            raise ValidationError({'estado': 'La confirmación debe realizarse desde el carrito.'})
        if not (user.is_superuser or user.role == 'ADMIN'):
            serializer.save(usuario=user, estado=Order.Estado.PENDIENTE)
        else:
            if serializer.validated_data.get('estado', Order.Estado.PENDIENTE) != Order.Estado.PENDIENTE:
                raise ValidationError({'estado': 'Un pedido directo debe iniciar pendiente.'})
            serializer.save(usuario=user, estado=Order.Estado.PENDIENTE)

    @transaction.atomic
    def perform_update(self, serializer):
        user = self.request.user
        instance = Order.objects.select_for_update().get(pk=serializer.instance.pk)
        serializer.instance = instance
        nuevo_estado = serializer.validated_data.get('estado', instance.estado)
        if not (user.is_superuser or user.role == 'ADMIN'):
            new_estado = self.request.data.get('estado')
            if new_estado is not None and new_estado != instance.estado:
                raise PermissionDenied(
                    "Solo el administrador puede cambiar el estado de un pedido."
                )
        direccion = serializer.validated_data.get('direccion_entrega', instance.direccion_entrega)
        if instance.estado != Order.Estado.PENDIENTE and direccion != instance.direccion_entrega:
            raise ValidationError({'direccion_entrega': 'El pedido ya no admite cambios de dirección.'})
        if nuevo_estado != instance.estado:
            allowed = {
                Order.Estado.PENDIENTE: {Order.Estado.CANCELADO},
                Order.Estado.CONFIRMADO: {Order.Estado.CANCELADO, Order.Estado.ENTREGADO},
                Order.Estado.CANCELADO: set(),
                Order.Estado.ENTREGADO: set(),
            }
            if nuevo_estado not in allowed.get(instance.estado, set()):
                raise ValidationError({'estado': 'Transición de estado no permitida; la confirmación se realiza desde el carrito.'})
            if nuevo_estado == Order.Estado.CANCELADO and instance.estado == Order.Estado.CONFIRMADO:
                if instance.huevos_descontados is None:
                    raise ValidationError({'estado': 'Pedido histórico sin registro de stock; requiere revisión manual.'})
                inventory = EggInventory.objects.select_for_update().filter(pk=1).first()
                if inventory is None:
                    raise ValidationError({'estado': 'La reserva de huevos no está configurada.'})
                if inventory.cantidad + instance.huevos_descontados > 2147483647:
                    raise ValidationError({'estado': 'La reposición excede la capacidad de la reserva.'})
                inventory.cantidad += instance.huevos_descontados
                inventory.save(update_fields=['cantidad', 'ultima_actualizacion'])
        serializer.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        pedido = Order.objects.select_for_update().get(pk=instance.pk)
        if pedido.estado != Order.Estado.PENDIENTE:
            raise PermissionDenied('El pedido ya no puede eliminarse.')
        pedido.delete()

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if not (user.is_superuser or user.role == 'ADMIN') and obj.usuario != user:
            raise PermissionDenied("No tienes acceso a este pedido.")
        return obj


# ----------------------------------------------------------------
# Cálculo automático del total de pedidos (conservado del TP2)
# ----------------------------------------------------------------
def validar_limite_total(total):
    field = Order._meta.get_field('total')
    maximum = Decimal(10) ** (field.max_digits - field.decimal_places) - Decimal(10) ** -field.decimal_places
    if total > maximum:
        raise ValidationError({'total': 'El total supera el máximo permitido para un pedido.'})


def validar_total_item(pedido, cantidad, precio, exclude_pk=None):
    items = pedido.items.exclude(pk=exclude_pk) if exclude_pk else pedido.items.all()
    total = sum((item.precio_unitario * item.cantidad for item in items), Decimal('0'))
    validar_limite_total(total + precio * cantidad)


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


# ----------------------------------------------------------------
# Ítems de pedido (protegidos por propiedad del pedido)
# ----------------------------------------------------------------
class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer

    def get_permissions(self):
        if self.action == 'list':
            self.permission_classes = [permissions.IsAuthenticated]
        elif self.action == 'retrieve':
            self.permission_classes = [
                permissions.IsAuthenticated, IsOwnerOrAdmin
            ]
        elif self.action == 'create':
            self.permission_classes = [permissions.IsAuthenticated]
        else:
            self.permission_classes = [IsOwnerOrAdmin]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        base = OrderItem.objects.select_related('pedido', 'producto').all()
        if self.action == 'list':
            if not (user.is_superuser or user.role == 'ADMIN'):
                base = base.filter(pedido__usuario=user)
            pedido = self.request.query_params.get('pedido')
            if pedido is not None:
                pedido_id = _filter_pk(pedido)
                base = base.filter(pedido_id=pedido_id) if pedido_id is not None else base.none()
        return base

    def _editable_order(self, pk):
        pedido = Order.objects.select_for_update().get(pk=pk)
        if pedido.estado != Order.Estado.PENDIENTE:
            raise PermissionDenied('El pedido ya no admite cambios en sus ítems.')
        return pedido

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        pedido = self._editable_order(serializer.validated_data['pedido'].pk)
        if pedido and not (user.is_superuser or user.role == 'ADMIN'):
            if pedido.usuario != user:
                raise PermissionDenied(
                    "No puedes agregar ítems a un pedido ajeno."
                )
        validar_total_item(pedido, serializer.validated_data['cantidad'], serializer.validated_data['producto'].precio)
        item = serializer.save(pedido=pedido)
        actualizar_total_pedido(item.pedido)

    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.instance
        pedido = self._editable_order(instance.pedido_id)
        instance.refresh_from_db()
        producto = serializer.validated_data.get('producto', instance.producto)
        precio = producto.precio if producto.pk != instance.producto_id else instance.precio_unitario
        cantidad = serializer.validated_data.get('cantidad', instance.cantidad)
        validar_total_item(pedido, cantidad, precio, exclude_pk=instance.pk)
        item = serializer.save()
        actualizar_total_pedido(pedido)

    @transaction.atomic
    def perform_destroy(self, instance):
        pedido = self._editable_order(instance.pedido_id)
        instance.delete()
        actualizar_total_pedido(pedido)

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if not (user.is_superuser or user.role == 'ADMIN'):
            if obj.pedido.usuario != user:
                raise PermissionDenied("No tienes acceso a este ítem de pedido.")
        return obj
