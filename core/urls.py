from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    ProductViewSet,
    StockViewSet,
    CartViewSet,
    CartItemViewSet,
    OrderViewSet,
    OrderItemViewSet,
    EggInventoryView,
)


router = DefaultRouter()

router.register(r'categorias', CategoryViewSet, basename='categoria')
router.register(r'productos', ProductViewSet, basename='producto')
router.register(r'stock', StockViewSet, basename='stock')
router.register(r'carritos', CartViewSet, basename='carrito')
router.register(r'items-carrito', CartItemViewSet, basename='item-carrito')
router.register(r'pedidos', OrderViewSet, basename='pedido')
router.register(r'items-pedido', OrderItemViewSet, basename='item-pedido')


urlpatterns = [
    path('inventario-huevos/', EggInventoryView.as_view(), name='inventario-huevos'),
    path('', include(router.urls)),
]
