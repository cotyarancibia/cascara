from django.db import models
from django.contrib.auth.models import AbstractUser


# Modelo de usuario
class User(AbstractUser):
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.username


# Modelo de categoría
class Category(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre


# Modelo de producto
class Product(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    categoria = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='productos'
    )

    disponible = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

# Modelo de stock
class Stock(models.Model):
    producto = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='stock'
    )
    cantidad = models.PositiveIntegerField(default=0)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.producto.nombre} - {self.cantidad} unidades"

# Modelo de carrito de compras
class Cart(models.Model):
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='carrito'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Carrito de {self.usuario.username}"
    
# Modelo de productos dentro del carrito
class CartItem(models.Model):
    carrito = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    producto = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='items_carrito'
    )
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['carrito', 'producto'],
                name='unique_producto_por_carrito'
            )
        ]

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"
    
# Modelo de pedido
class Order(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('CONFIRMADO', 'Confirmado'),
        ('ENTREGADO', 'Entregado'),
        ('CANCELADO', 'Cancelado'),
    ]

    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='pedidos'
    )
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='PENDIENTE'
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    direccion_entrega = models.CharField(max_length=255)

    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.username}"
    
# Modelo de detalle del pedido
class OrderItem(models.Model):
    pedido = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    producto = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='items_pedido'
    )
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} - Pedido #{self.pedido.id}"