from apps.inventory.models import Item


def low_stock_count(request):
    if not request.user.is_authenticated:
        return {'low_stock_count': 0}
    count = Item.objects.filter(status__in=['low_stock', 'out_of_stock']).count()
    return {'low_stock_count': count}
