import pytest
from apps.inventory.models import Item


def make_item(**kwargs):
    defaults = dict(
        name='Widget',
        category='General',
        quantity=10,
        reorder_level=5,
        purchase_price='9.99',
        currency='GEL',
    )
    defaults.update(kwargs)
    item = Item(**defaults)
    item.save()
    return item


@pytest.mark.django_db
class TestItemStatus:
    def test_in_stock_when_above_reorder_level(self):
        item = make_item(quantity=10, reorder_level=5)
        assert item.status == 'in_stock'

    def test_low_stock_when_at_reorder_level(self):
        item = make_item(quantity=5, reorder_level=5)
        assert item.status == 'low_stock'

    def test_low_stock_when_below_reorder_level(self):
        item = make_item(quantity=3, reorder_level=5)
        assert item.status == 'low_stock'

    def test_out_of_stock_when_zero(self):
        item = make_item(quantity=0, reorder_level=5)
        assert item.status == 'out_of_stock'

    def test_status_updates_on_save(self):
        item = make_item(quantity=10, reorder_level=5)
        assert item.status == 'in_stock'
        item.quantity = 0
        item.save()
        assert item.status == 'out_of_stock'


@pytest.mark.django_db
class TestItemSKU:
    def test_sku_auto_generated_when_blank(self):
        item = make_item(name='Laptop')
        assert item.sku != ''
        assert item.sku.startswith('LAPT-')

    def test_sku_uses_first_four_chars_of_name(self):
        item = make_item(name='Monitor Stand')
        assert item.sku.startswith('MONI-')

    def test_sku_preserved_if_provided(self):
        item = Item(
            name='Widget', category='General', quantity=5,
            reorder_level=2, purchase_price='5.00', sku='CUSTOM-001',
        )
        item.save()
        assert item.sku == 'CUSTOM-001'

    def test_two_items_with_same_name_get_unique_skus(self):
        item1 = make_item(name='Chair')
        item2 = make_item(name='Chair')
        assert item1.sku != item2.sku
