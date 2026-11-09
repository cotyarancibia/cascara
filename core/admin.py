from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
from django.db import transaction
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


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Información adicional', {
            'fields': ('telefono', 'direccion', 'role'),
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información adicional', {
            'fields': ('telefono', 'direccion', 'role'),
        }),
    )
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Stock)
admin.site.register(Cart)
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    @transaction.atomic
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        if request.method == 'POST':
            original = (CartItem.objects.filter(pk=object_id).values_list('carrito_id', flat=True).first()
                        if object_id else None)
            destino = request.POST.get('carrito')
            cart_ids = {int(value) for value in (original, destino) if value and str(value).isdigit()}
            list(Cart.objects.select_for_update().filter(pk__in=cart_ids).order_by('pk'))
        return super().changeform_view(request, object_id, form_url, extra_context)

    @transaction.atomic
    def delete_view(self, request, object_id, extra_context=None):
        if request.method == 'POST':
            cart_id = CartItem.objects.filter(pk=object_id).values_list('carrito_id', flat=True).first()
            if cart_id:
                list(Cart.objects.select_for_update().filter(pk=cart_id))
        return super().delete_view(request, object_id, extra_context)

    @transaction.atomic
    def delete_queryset(self, request, queryset):
        cart_ids = list(queryset.values_list('carrito_id', flat=True).distinct())
        list(Cart.objects.select_for_update().filter(pk__in=cart_ids).order_by('pk'))
        return super().delete_queryset(request, queryset)

class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = '__all__'

    def clean_estado(self):
        estado = self.cleaned_data['estado']
        anterior = Order.objects.filter(pk=self.instance.pk).values_list('estado', flat=True).first()
        if estado == Order.Estado.CONFIRMADO and anterior != Order.Estado.CONFIRMADO:
            raise forms.ValidationError('La confirmación debe realizarse desde el carrito.')
        return estado


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm


admin.site.register(OrderItem)
