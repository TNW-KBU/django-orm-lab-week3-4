from django.contrib import admin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'max_allowed_price', 'stock_quantity',
                    'reorder_level', 'is_promotional', 'status', 'warehouse_country',
                    'total_sold', 'total_revenue')
    list_filter = ('category', 'status', 'is_promotional', 'warehouse_country')
    search_fields = ('name',)
