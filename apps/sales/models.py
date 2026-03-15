from decimal import Decimal
from django.db import models
from apps.inventory.models import Item


class Sale(models.Model):
    CURRENCY_CHOICES = [('GEL', 'GEL'), ('USD', 'USD')]

    buyer_name = models.CharField(max_length=255, blank=True)
    note = models.TextField(blank=True)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_profit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='GEL')
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_totals(self):
        revenue = Decimal('0.00')
        cost = Decimal('0.00')
        for line in self.items.all():
            revenue += line.sale_price * line.quantity
            cost += line.cost_price * line.quantity
        self.total_revenue = revenue
        self.total_cost = cost
        self.total_profit = revenue - cost

    def __str__(self):
        return f"Sale #{self.pk} — {self.buyer_name or 'Anonymous'} ({self.created_at:%Y-%m-%d})"

    class Meta:
        ordering = ['-created_at']


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='sale_items')
    quantity = models.IntegerField()
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.item.name} @ {self.sale_price}"
