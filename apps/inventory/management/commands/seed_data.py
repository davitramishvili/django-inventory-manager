"""
Usage: python manage.py seed_data
Creates sample inventory items and sales so the dashboard has real data to display.
Safe to run multiple times — skips items that already exist by SKU.
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.inventory.models import Item
from apps.sales.models import Sale, SaleItem


ITEMS = [
    dict(name="Laptop Pro 15",     category="Electronics", quantity=12, reorder_level=3,  purchase_price="850.00",  currency="USD"),
    dict(name="Wireless Mouse",    category="Electronics", quantity=4,  reorder_level=5,  purchase_price="12.50",   currency="USD"),
    dict(name="Office Chair",      category="Furniture",   quantity=7,  reorder_level=2,  purchase_price="180.00",  currency="GEL"),
    dict(name="Standing Desk",     category="Furniture",   quantity=2,  reorder_level=3,  purchase_price="420.00",  currency="GEL"),
    dict(name="USB-C Hub",         category="Electronics", quantity=0,  reorder_level=5,  purchase_price="35.00",   currency="USD"),
    dict(name="Notebook A5",       category="Stationery",  quantity=50, reorder_level=10, purchase_price="2.50",    currency="GEL"),
    dict(name="Monitor 27\"",      category="Electronics", quantity=5,  reorder_level=2,  purchase_price="310.00",  currency="USD"),
    dict(name="Mechanical Keyboard",category="Electronics",quantity=3,  reorder_level=4,  purchase_price="75.00",   currency="USD"),
    dict(name="Desk Lamp",         category="Furniture",   quantity=8,  reorder_level=3,  purchase_price="45.00",   currency="GEL"),
    dict(name="Ballpoint Pens x10",category="Stationery",  quantity=30, reorder_level=10, purchase_price="4.00",    currency="GEL"),
]


class Command(BaseCommand):
    help = "Seed the database with sample inventory items and sales."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Seeding inventory items...")
        created_items = {}

        for data in ITEMS:
            # Generate the SKU the same way the model does, then check for existence
            prefix = data['name'][:4].upper().replace(' ', '')
            existing = Item.objects.filter(name=data['name']).first()
            if existing:
                self.stdout.write(f"  skip — {data['name']} already exists")
                created_items[data['name']] = existing
                continue

            item = Item(**data)
            item.save()
            created_items[data['name']] = item
            self.stdout.write(self.style.SUCCESS(f"  + {item.name} [{item.sku}] qty={item.quantity} status={item.status}"))

        self.stdout.write("\nSeeding sales...")

        sales_data = [
            {
                "buyer_name": "Giorgi Beridze",
                "currency": "USD",
                "lines": [
                    ("Laptop Pro 15",      1, "1100.00"),
                    ("Wireless Mouse",     2, "22.00"),
                ],
            },
            {
                "buyer_name": "Nino Kvaratskhelia",
                "currency": "GEL",
                "lines": [
                    ("Office Chair",       1, "280.00"),
                    ("Desk Lamp",          2, "70.00"),
                ],
            },
            {
                "buyer_name": "Walk-in Customer",
                "currency": "USD",
                "lines": [
                    ("USB-C Hub",          0, "50.00"),   # 0 qty — will be skipped (out of stock)
                    ("Monitor 27\"",       1, "450.00"),
                ],
            },
            {
                "buyer_name": "Luka Tskitishvili",
                "currency": "GEL",
                "lines": [
                    ("Notebook A5",        5, "5.00"),
                    ("Ballpoint Pens x10", 3, "7.00"),
                ],
            },
            {
                "buyer_name": "Mariam Jokhadze",
                "currency": "USD",
                "lines": [
                    ("Mechanical Keyboard", 1, "120.00"),
                ],
            },
        ]

        for sale_data in sales_data:
            sale = Sale.objects.create(
                buyer_name=sale_data["buyer_name"],
                currency=sale_data["currency"],
            )
            created_lines = 0
            for item_name, qty, sale_price in sale_data["lines"]:
                item = created_items.get(item_name)
                if not item or item.quantity < qty or qty == 0:
                    self.stdout.write(f"  skip line — {item_name} (qty={qty}, stock={item.quantity if item else '?'})")
                    continue

                SaleItem.objects.create(
                    sale=sale,
                    item=item,
                    quantity=qty,
                    sale_price=Decimal(sale_price),
                    cost_price=item.purchase_price,
                )
                item.quantity -= qty
                item.save()
                created_lines += 1

            if created_lines:
                sale.calculate_totals()
                sale.save()
                self.stdout.write(self.style.SUCCESS(
                    f"  + Sale #{sale.pk} — {sale.buyer_name} "
                    f"revenue={sale.currency} {sale.total_revenue} profit={sale.total_profit}"
                ))
            else:
                sale.delete()
                self.stdout.write(f"  removed empty sale for {sale_data['buyer_name']}")

        self.stdout.write(self.style.SUCCESS("\nDone. Open http://127.0.0.1:8000/dashboard/ to see results."))
