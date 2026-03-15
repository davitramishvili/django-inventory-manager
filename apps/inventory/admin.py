from django.contrib import admin
from .models import Item

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'quantity', 'status', 'currency', 'purchase_price')
    list_filter = ('status', 'currency', 'category')
    search_fields = ('name', 'sku')
