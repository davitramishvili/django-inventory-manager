from django.db import transaction
from rest_framework import viewsets, permissions, mixins

from .models import Sale
from .serializers import SaleSerializer


class SaleViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SaleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Sale.objects.prefetch_related('items__item').all()
        buyer = self.request.query_params.get('buyer')
        date_start = self.request.query_params.get('start')
        date_end = self.request.query_params.get('end')
        if buyer:
            queryset = queryset.filter(buyer_name__icontains=buyer)
        if date_start:
            queryset = queryset.filter(created_at__date__gte=date_start)
        if date_end:
            queryset = queryset.filter(created_at__date__lte=date_end)
        return queryset

    @transaction.atomic
    def perform_destroy(self, instance):
        # Restore stock for every line item before deleting
        for line in instance.items.select_related('item').all():
            item = line.item
            item.quantity += line.quantity
            item.save()
        instance.delete()
