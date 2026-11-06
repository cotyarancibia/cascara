from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from django.db import IntegrityError, transaction
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


# ----------------------------------------------------------------
# Ítems del carrito (misma restricción de propiedad)
# ----------------------------------------------------------------
class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsCliente, IsOwnerOrAdmin]

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
                serializer.save(carrito=carrito)
        except IntegrityError:
            raise ValidationError({'producto': 'No se pudo agregar el producto al carrito.'})

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
        base = Order.objects.all()
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
        if not (user.is_superuser or user.role == 'ADMIN'):
            serializer.save(usuario=user, estado=Order.Estado.PENDIENTE)
        else:
            serializer.save(usuario=user)

    @transaction.atomic
    def perform_update(self, serializer):
        user = self.request.user
        instance = Order.objects.select_for_update().get(pk=serializer.instance.pk)
        serializer.instance = instance
        # Solo ADMIN puede cambiar el estado del pedido.
        if not (user.is_superuser or user.role == 'ADMIN'):
            new_estado = self.request.data.get('estado')
            if new_estado is not None and new_estado != instance.estado:
                raise PermissionDenied(
                    "Solo el administrador puede cambiar el estado de un pedido."
                )
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
            if user.is_superuser or user.role == 'ADMIN':
                return base
            return base.filter(pedido__usuario=user)
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
        item = serializer.save(pedido=pedido)
        actualizar_total_pedido(item.pedido)

    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.instance
        pedido = self._editable_order(instance.pedido_id)
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
