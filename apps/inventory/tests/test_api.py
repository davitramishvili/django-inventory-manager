import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from apps.inventory.models import Item


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='tester', password='pass1234')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def item(db):
    i = Item(name='Desk', category='Furniture', quantity=20,
             reorder_level=5, purchase_price='150.00', currency='GEL')
    i.save()
    return i


LIST_URL = '/api/inventory/items/'


def detail_url(pk):
    return f'/api/inventory/items/{pk}/'


@pytest.mark.django_db
class TestItemListCreate:
    def test_unauthenticated_returns_401(self, api_client):
        resp = api_client.get(LIST_URL)
        assert resp.status_code == 401

    def test_list_returns_200(self, auth_client, item):
        resp = auth_client.get(LIST_URL)
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_create_returns_201_with_auto_sku(self, auth_client):
        payload = {
            'name': 'Monitor',
            'category': 'Electronics',
            'quantity': 15,
            'reorder_level': 3,
            'purchase_price': '299.99',
            'currency': 'GEL',
        }
        resp = auth_client.post(LIST_URL, payload)
        assert resp.status_code == 201
        assert resp.data['sku'] != ''
        assert resp.data['status'] == 'in_stock'

    def test_create_requires_name(self, auth_client):
        resp = auth_client.post(LIST_URL, {'category': 'X', 'purchase_price': '10'})
        assert resp.status_code == 400

    def test_filter_by_status(self, auth_client, item):
        # item has quantity=20, reorder=5 → in_stock
        resp = auth_client.get(LIST_URL + '?status=in_stock')
        assert resp.status_code == 200
        assert any(i['id'] == item.pk for i in resp.data)

        resp2 = auth_client.get(LIST_URL + '?status=low_stock')
        assert all(i['id'] != item.pk for i in resp2.data)

    def test_filter_by_category(self, auth_client, item):
        resp = auth_client.get(LIST_URL + '?category=Furniture')
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]['id'] == item.pk

    def test_filter_by_category_case_insensitive(self, auth_client, item):
        resp = auth_client.get(LIST_URL + '?category=furniture')
        assert resp.status_code == 200
        assert len(resp.data) == 1


@pytest.mark.django_db
class TestItemRetrieveUpdateDelete:
    def test_retrieve_returns_200(self, auth_client, item):
        resp = auth_client.get(detail_url(item.pk))
        assert resp.status_code == 200
        assert resp.data['name'] == 'Desk'

    def test_patch_quantity_updates_status(self, auth_client, item):
        # Drop quantity to reorder_level → low_stock
        resp = auth_client.patch(detail_url(item.pk), {'quantity': 5})
        assert resp.status_code == 200
        assert resp.data['status'] == 'low_stock'

    def test_patch_quantity_to_zero_is_out_of_stock(self, auth_client, item):
        resp = auth_client.patch(detail_url(item.pk), {'quantity': 0})
        assert resp.status_code == 200
        assert resp.data['status'] == 'out_of_stock'

    def test_delete_returns_204(self, auth_client, item):
        resp = auth_client.delete(detail_url(item.pk))
        assert resp.status_code == 204
        assert not Item.objects.filter(pk=item.pk).exists()
