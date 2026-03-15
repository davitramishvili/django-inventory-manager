from django.db.models import F
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.models import Item
from apps.inventory.serializers import ItemSerializer
from .models import DailySummary
from .serializers import DailySummarySerializer


class DailySummaryView(APIView):
    """
    GET /api/reports/daily/?date=YYYY-MM-DD        → single day
    GET /api/reports/daily/?start=YYYY-MM-DD&end=YYYY-MM-DD → date range
    """

    def get(self, request):
        date_param = request.query_params.get('date')
        start_param = request.query_params.get('start')
        end_param = request.query_params.get('end')

        if date_param:
            try:
                summary = DailySummary.objects.get(date=date_param)
            except DailySummary.DoesNotExist:
                return Response(
                    {'detail': f'No summary found for {date_param}.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(DailySummarySerializer(summary).data)

        if start_param and end_param:
            summaries = DailySummary.objects.filter(date__range=[start_param, end_param])
            return Response(DailySummarySerializer(summaries, many=True).data)

        return Response(
            {'detail': 'Provide ?date=YYYY-MM-DD or ?start=YYYY-MM-DD&end=YYYY-MM-DD'},
            status=status.HTTP_400_BAD_REQUEST,
        )


class LowStockView(APIView):
    """
    GET /api/reports/low-stock/
    Returns all items where quantity <= reorder_level.
    """

    def get(self, request):
        low_items = Item.objects.filter(quantity__lte=F('reorder_level'))
        return Response(ItemSerializer(low_items, many=True).data)
