from django.urls import path
from .views import DailySummaryView, LowStockView

urlpatterns = [
    path('daily/', DailySummaryView.as_view(), name='reports-daily'),
    path('low-stock/', LowStockView.as_view(), name='reports-low-stock'),
]
