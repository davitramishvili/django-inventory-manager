from django.db import models


class DailySummary(models.Model):
    date = models.DateField(unique=True)
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    items_sold = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Summary {self.date} — profit {self.total_profit}"

    class Meta:
        ordering = ['-date']
