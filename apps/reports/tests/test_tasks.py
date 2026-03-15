from decimal import Decimal
from datetime import date, timedelta
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.inventory.models import Item
from apps.reports.models import DailySummary
from apps.reports.tasks import calculate_daily_summary, check_low_stock
from apps.sales.models import Sale, SaleItem


def make_item(quantity=20, price='10.00', reorder_level=5):
    i = Item(name='Widget', category='General', quantity=quantity,
             reorder_level=reorder_level, purchase_price=price, currency='GEL')
    i.save()
    return i


def make_sale(item, qty=5, sale_price='15.00', cost_price='10.00', days_ago=0):
    """Creates a Sale with one SaleItem, posted days_ago days in the past."""
    from django.utils import timezone
    sale = Sale.objects.create(currency='GEL')
    SaleItem.objects.create(sale=sale, item=item, quantity=qty,
                            sale_price=Decimal(sale_price), cost_price=Decimal(cost_price))
    sale.calculate_totals()
    sale.save()

    if days_ago:
        # Backdate created_at so we can test date-range filtering
        target = timezone.now() - timedelta(days=days_ago)
        Sale.objects.filter(pk=sale.pk).update(created_at=target)
        sale.refresh_from_db()

    return sale


@pytest.mark.django_db
class TestCalculateDailySummary:
    def test_creates_summary_row(self):
        item = make_item()
        sale = make_sale(item, qty=3, sale_price='20.00', cost_price='10.00')
        target = sale.created_at.date().isoformat()

        result = calculate_daily_summary(target_date=target)

        assert DailySummary.objects.filter(date=target).exists()
        summary = DailySummary.objects.get(date=target)
        assert summary.total_revenue == Decimal('60.00')  # 3 * 20
        assert summary.total_cost == Decimal('30.00')     # 3 * 10
        assert summary.total_profit == Decimal('30.00')   # 60 - 30
        assert summary.items_sold == 3

    def test_updates_existing_summary_row(self):
        target = date.today().isoformat()
        DailySummary.objects.create(date=target, total_revenue=Decimal('999.00'))

        calculate_daily_summary(target_date=target)

        assert DailySummary.objects.filter(date=target).count() == 1

    def test_empty_day_produces_zero_summary(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        calculate_daily_summary(target_date=yesterday)

        summary = DailySummary.objects.get(date=yesterday)
        assert summary.total_revenue == Decimal('0.00')
        assert summary.items_sold == 0

    def test_returns_dict_with_date_and_profit(self):
        target = date.today().isoformat()
        result = calculate_daily_summary(target_date=target)
        assert result['date'] == target
        assert 'profit' in result


@pytest.mark.django_db
class TestCheckLowStock:
    def test_returns_count_of_low_stock_items(self):
        make_item(quantity=3, reorder_level=5)   # low_stock
        make_item(quantity=0, reorder_level=5)   # out_of_stock (qty <= reorder_level)
        make_item(quantity=20, reorder_level=5)  # in_stock — should NOT be counted

        result = check_low_stock()
        assert result['low_stock_items'] == 2

    def test_updates_status_field(self):
        # Create item with quantity at reorder level but wrong status manually set
        item = make_item(quantity=5, reorder_level=5)
        # Force wrong status to verify task corrects it
        Item.objects.filter(pk=item.pk).update(status='in_stock')

        check_low_stock()

        item.refresh_from_db()
        assert item.status == 'low_stock'

    def test_no_low_stock_returns_zero(self):
        make_item(quantity=100, reorder_level=5)
        result = check_low_stock()
        assert result['low_stock_items'] == 0


@pytest.mark.django_db
class TestReportsAPI:
    """Smoke-tests for the reports REST endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        user = User.objects.create_user(username='tester', password='pass1234')
        self.client = APIClient()
        self.client.force_authenticate(user=user)

    def test_daily_summary_missing_params_returns_400(self):
        resp = self.client.get('/api/reports/daily/')
        assert resp.status_code == 400

    def test_daily_summary_not_found_returns_404(self):
        resp = self.client.get('/api/reports/daily/?date=2000-01-01')
        assert resp.status_code == 404

    def test_daily_summary_date_param(self):
        target = date.today().isoformat()
        DailySummary.objects.create(date=target, total_revenue=Decimal('100.00'))
        resp = self.client.get(f'/api/reports/daily/?date={target}')
        assert resp.status_code == 200
        assert Decimal(resp.data['total_revenue']) == Decimal('100.00')

    def test_daily_summary_range_param(self):
        DailySummary.objects.create(date='2025-01-01')
        DailySummary.objects.create(date='2025-01-02')
        DailySummary.objects.create(date='2025-01-03')
        resp = self.client.get('/api/reports/daily/?start=2025-01-01&end=2025-01-02')
        assert resp.status_code == 200
        assert len(resp.data) == 2

    def test_low_stock_returns_200(self):
        resp = self.client.get('/api/reports/low-stock/')
        assert resp.status_code == 200

    def test_low_stock_lists_flagged_items(self):
        make_item(quantity=2, reorder_level=5)   # low
        make_item(quantity=50, reorder_level=5)  # fine

        resp = self.client.get('/api/reports/low-stock/')
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_unauthenticated_returns_401(self):
        resp = APIClient().get('/api/reports/low-stock/')
        assert resp.status_code == 401
