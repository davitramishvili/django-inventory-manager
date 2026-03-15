from rest_framework import serializers
from .models import DailySummary


class DailySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailySummary
        fields = ['id', 'date', 'total_revenue', 'total_cost', 'total_profit', 'items_sold', 'created_at']
        read_only_fields = fields
