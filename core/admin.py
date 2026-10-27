from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User,
    Category,
    Product,
    Stock,
    Cart,
    CartItem,
    Order,
    OrderItem,
)


admin.site.register(User, UserAdmin)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Stock)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)