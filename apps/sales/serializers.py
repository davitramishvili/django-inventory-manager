from django.db import transaction
from rest_framework import serializers
from apps.inventory.models import Item
from .models import Sale, SaleItem


class SaleItemReadSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_sku = serializers.CharField(source='item.sku', read_only=True)

    class Meta:
        model = SaleItem
        fields = ['id', 'item', 'item_name', 'item_sku', 'quantity', 'sale_price', 'cost_price']


class SaleItemWriteSerializer(serializers.Serializer):
    item = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    sale_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemReadSerializer(many=True, read_only=True)
    sale_items = SaleItemWriteSerializer(many=True, write_only=True)

    class Meta:
        model = Sale
        fields = [
            'id', 'buyer_name', 'note', 'currency',
            'total_revenue', 'total_cost', 'total_profit',
            'created_at', 'items', 'sale_items',
        ]
        read_only_fields = ['total_revenue', 'total_cost', 'total_profit', 'created_at']

    def validate_sale_items(self, value):
        if not value:
            raise serializers.ValidationError("A sale must include at least one item.")

        # Check for duplicate items in the same sale
        item_ids = [entry['item'].pk for entry in value]
        if len(item_ids) != len(set(item_ids)):
            raise serializers.ValidationError("Duplicate items in the same sale are not allowed.")

        # Validate stock availability for each line
        errors = []
        for entry in value:
            item = entry['item']
            if item.quantity < entry['quantity']:
                errors.append(
                    f"'{item.name}' only has {item.quantity} units in stock "
                    f"(requested {entry['quantity']})."
                )
        if errors:
            raise serializers.ValidationError(errors)

        return value

    @transaction.atomic
    def create(self, validated_data):
        sale_items_data = validated_data.pop('sale_items')

        sale = Sale.objects.create(**validated_data)

        for entry in sale_items_data:
            item = entry['item']
            qty = entry['quantity']

            SaleItem.objects.create(
                sale=sale,
                item=item,
                quantity=qty,
                sale_price=entry['sale_price'],
                cost_price=item.purchase_price,  # snapshot at time of sale
            )

            # Deduct stock — Item.save() will auto-update status
            item.quantity -= qty
            item.save()

        sale.calculate_totals()
        sale.save()

        return sale
