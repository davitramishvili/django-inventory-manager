from decimal import Decimal
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from apps.inventory.models import Item
from apps.sales.models import Sale


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='tester', password='pass1234')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def item(db):
    i = Item(name='Keyboard', category='Electronics', quantity=30,
             reorder_level=5, purchase_price='25.00', currency='GEL')
    i.save()
    return i


SALES_URL = '/api/sales/'


def sale_payload(item_pk, quantity=2, sale_price='50.00', buyer='Test Buyer'):
    return {
        'buyer_name': buyer,
        'currency': 'GEL',
        'sale_items': [
            {'item': item_pk, 'quantity': quantity, 'sale_price': sale_price}
        ],
    }


@pytest.mark.django_db
class TestCreateSale:
    def test_create_sale_returns_201(self, auth_client, item):
        resp = auth_client.post(SALES_URL, sale_payload(item.pk), format='json')
        assert resp.status_code == 201

    def test_create_sale_deducts_stock(self, auth_client, item):
        auth_client.post(SALES_URL, sale_payload(item.pk, quantity=5), format='json')
        item.refresh_from_db()
        assert item.quantity == 25  # 30 - 5

    def test_create_sale_snapshots_cost_price(self, auth_client, item):
        resp = auth_client.post(SALES_URL, sale_payload(item.pk, quantity=1), format='json')
        assert resp.status_code == 201
        line = resp.data['items'][0]
        assert Decimal(str(line['cost_price'])) == Decimal(str(item.purchase_price))

    def test_create_sale_calculates_profit(self, auth_client, item):
        # sell 2 at 50, cost is 25 each → profit = (50-25)*2 = 50
        resp = auth_client.post(SALES_URL, sale_payload(item.pk, quantity=2, sale_price='50.00'), format='json')
        assert Decimal(resp.data['total_profit']) == Decimal('50.00')

    def test_create_sale_insufficient_stock_returns_400(self, auth_client, item):
        resp = auth_client.post(SALES_URL, sale_payload(item.pk, quantity=999), format='json')
        assert resp.status_code == 400

    def test_create_sale_empty_items_returns_400(self, auth_client):
        resp = auth_client.post(SALES_URL, {'buyer_name': 'X', 'currency': 'GEL', 'sale_items': []}, format='json')
        assert resp.status_code == 400

    def test_create_sale_duplicate_items_returns_400(self, auth_client, item):
        payload = {
            'buyer_name': 'X',
            'currency': 'GEL',
            'sale_items': [
                {'item': item.pk, 'quantity': 1, 'sale_price': '50.00'},
                {'item': item.pk, 'quantity': 1, 'sale_price': '50.00'},
            ],
        }
        resp = auth_client.post(SALES_URL, payload, format='json')
        assert resp.status_code == 400

    def test_create_sale_updates_item_status(self, auth_client, item):
        # Drain all but reorder_level to trigger low_stock
        qty_to_sell = item.quantity - item.reorder_level
        auth_client.post(SALES_URL, sale_payload(item.pk, quantity=qty_to_sell), format='json')
        item.refresh_from_db()
        assert item.status == 'low_stock'

    def test_unauthenticated_returns_401(self):
        client = APIClient()
        resp = client.post(SALES_URL, {}, format='json')
        assert resp.status_code == 401


@pytest.mark.django_db
class TestDeleteSale:
    def test_delete_sale_restores_stock(self, auth_client, item):
        original_qty = item.quantity
        resp = auth_client.post(SALES_URL, sale_payload(item.pk, quantity=5), format='json')
        sale_id = resp.data['id']

        auth_client.delete(f'{SALES_URL}{sale_id}/')
        item.refresh_from_db()
        assert item.quantity == original_qty

    def test_delete_sale_updates_item_status(self, auth_client, item):
        # Sell until low_stock
        qty_to_sell = item.quantity - item.reorder_level
        resp = auth_client.post(SALES_URL, sale_payload(item.pk, quantity=qty_to_sell), format='json')
        item.refresh_from_db()
        assert item.status == 'low_stock'

        # Restore by deleting the sale
        auth_client.delete(f'{SALES_URL}{resp.data["id"]}/')
        item.refresh_from_db()
        assert item.status == 'in_stock'

    def test_delete_sale_returns_204(self, auth_client, item):
        resp = auth_client.post(SALES_URL, sale_payload(item.pk, quantity=1), format='json')
        del_resp = auth_client.delete(f'{SALES_URL}{resp.data["id"]}/')
        assert del_resp.status_code == 204


@pytest.mark.django_db
class TestListSales:
    def test_list_returns_200(self, auth_client):
        resp = auth_client.get(SALES_URL)
        assert resp.status_code == 200

    def test_filter_by_buyer(self, auth_client, item):
        auth_client.post(SALES_URL, sale_payload(item.pk, quantity=1, buyer='Alice'), format='json')

        # add another item for second sale
        item2 = Item(name='Mouse', category='Electronics', quantity=10,
                     reorder_level=2, purchase_price='15.00', currency='GEL')
        item2.save()
        auth_client.post(SALES_URL, sale_payload(item2.pk, quantity=1, buyer='Bob'), format='json')

        resp = auth_client.get(SALES_URL + '?buyer=alice')
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]['buyer_name'] == 'Alice'
