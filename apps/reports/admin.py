from django.contrib import admin
from .models import DailySummary


@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_revenue', 'total_cost', 'total_profit', 'items_sold']
    ordering = ['-date']
