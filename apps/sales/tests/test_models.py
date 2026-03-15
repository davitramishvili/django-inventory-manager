from decimal import Decimal
import pytest
from apps.inventory.models import Item
from apps.sales.models import Sale, SaleItem


def make_item(quantity=20, price='10.00'):
    i = Item(name='Widget', category='General', quantity=quantity,
             reorder_level=5, purchase_price=price, currency='GEL')
    i.save()
    return i


@pytest.mark.django_db
class TestSaleCalculateTotals:
    def test_totals_calculated_correctly(self):
        item = make_item(quantity=50, price='10.00')
        sale = Sale.objects.create(currency='GEL')
        SaleItem.objects.create(sale=sale, item=item, quantity=3,
                                sale_price=Decimal('15.00'), cost_price=Decimal('10.00'))
        SaleItem.objects.create(sale=sale, item=item, quantity=2,
                                sale_price=Decimal('20.00'), cost_price=Decimal('10.00'))
        sale.calculate_totals()
        # revenue: 3*15 + 2*20 = 45 + 40 = 85
        assert sale.total_revenue == Decimal('85.00')
        # cost: 3*10 + 2*10 = 50
        assert sale.total_cost == Decimal('50.00')
        # profit: 85 - 50 = 35
        assert sale.total_profit == Decimal('35.00')

    def test_empty_sale_has_zero_totals(self):
        sale = Sale.objects.create(currency='GEL')
        sale.calculate_totals()
        assert sale.total_revenue == Decimal('0.00')
        assert sale.total_cost == Decimal('0.00')
        assert sale.total_profit == Decimal('0.00')
