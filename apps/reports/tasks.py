import logging
from datetime import date, timedelta
from decimal import Decimal

from celery import shared_task
from django.db.models import F, Sum

from apps.inventory.models import Item
from apps.sales.models import Sale
from .models import DailySummary

logger = logging.getLogger(__name__)


@shared_task
def calculate_daily_summary(target_date=None):
    """
    Aggregate all sales for target_date into a DailySummary row.
    Runs nightly at midnight via Celery Beat.
    Defaults to yesterday so it captures a completed day.
    """
    if target_date is None:
        target_date = (date.today() - timedelta(days=1)).isoformat()

    sales = Sale.objects.filter(created_at__date=target_date)

    totals = sales.aggregate(
        revenue=Sum('total_revenue'),
        cost=Sum('total_cost'),
        profit=Sum('total_profit'),
    )

    items_sold = sum(
        sale.items.aggregate(total=Sum('quantity'))['total'] or 0
        for sale in sales
    )

    summary, created = DailySummary.objects.update_or_create(
        date=target_date,
        defaults={
            'total_revenue': totals['revenue'] or Decimal('0.00'),
            'total_cost': totals['cost'] or Decimal('0.00'),
            'total_profit': totals['profit'] or Decimal('0.00'),
            'items_sold': items_sold,
        },
    )

    action = 'Created' if created else 'Updated'
    logger.info("%s daily summary for %s — profit %s", action, target_date, summary.total_profit)
    return {'date': str(target_date), 'profit': str(summary.total_profit)}


@shared_task
def check_low_stock():
    """
    Log a warning for every item at or below its reorder level and
    re-save each one so the status field stays accurate.
    Runs every morning at 8am via Celery Beat.
    """
    # F('reorder_level') lets PostgreSQL compare the two columns directly
    low_items = Item.objects.filter(quantity__lte=F('reorder_level'))

    count = 0
    for item in low_items:
        item.save()  # triggers status auto-update defined in Item.save()
        logger.warning(
            "LOW STOCK: %s (SKU: %s) — qty=%d, reorder_level=%d",
            item.name, item.sku, item.quantity, item.reorder_level,
        )
        count += 1

    logger.info("check_low_stock complete — %d items flagged", count)
    return {'low_stock_items': count}
