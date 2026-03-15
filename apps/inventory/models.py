import uuid
from django.db import models


class Item(models.Model):
    CURRENCY_CHOICES = [('GEL', 'GEL'), ('USD', 'USD')]
    STATUS_CHOICES = [
        ('in_stock', 'In Stock'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
    ]

    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True, blank=True)
    category = models.CharField(max_length=100)
    quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=5)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='GEL')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_stock')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.sku:
            prefix = self.name[:4].upper().replace(' ', '')
            self.sku = f"{prefix}-{uuid.uuid4().hex[:6].upper()}"

        if self.quantity == 0:
            self.status = 'out_of_stock'
        elif self.quantity <= self.reorder_level:
            self.status = 'low_stock'
        else:
            self.status = 'in_stock'

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    class Meta:
        ordering = ['name']
