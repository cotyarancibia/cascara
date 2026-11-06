"""Permisos personalizados basados en roles y propiedad de objetos."""

from rest_framework import permissions


class IsAuthenticatedRole(permissions.BasePermission):
    """El usuario debe estar autenticado."""

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated
        )


class IsAdmin(permissions.BasePermission):
    """Solo el rol ADMIN (o superusuario) puede acceder."""

    message = "Solo el administrador puede realizar esta acción."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.role == 'ADMIN'
            )
        )


class IsAdminOrVendedor(permissions.BasePermission):
    """Solo los roles ADMIN y VENDEDOR pueden acceder."""

    message = (
        "Solo administradores y vendedores pueden realizar esta acción."
    )

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.role in ('ADMIN', 'VENDEDOR')
            )
        )


class IsCliente(permissions.BasePermission):
    """Solo el rol CLIENTE puede acceder."""

    message = "Solo clientes pueden realizar esta acción."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'CLIENTE'
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """El dueño del objeto (campo `usuario`) o un ADMIN puede acceder."""

    message = "No tienes permiso sobre este recurso."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.role == 'ADMIN':
            return True
        owner = getattr(obj, 'usuario', None)
        if owner is None and hasattr(obj, 'carrito'):
            owner = obj.carrito.usuario
        if owner is None and hasattr(obj, 'pedido'):
            owner = obj.pedido.usuario
        return owner == user
