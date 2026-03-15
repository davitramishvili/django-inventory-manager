import json
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import UserProfile, log_activity
from apps.inventory.models import Item
from apps.sales.models import Sale, SaleItem
from .decorators import admin_required, employee_required


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_role(user):
    if user.is_superuser:
        return 'admin'
    try:
        return user.profile.role
    except Exception:
        return 'user'


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        role = _get_role(request.user)
        return redirect('dashboard' if role in ('admin', 'employee') else 'catalog')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            role = _get_role(user)
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard' if role in ('admin', 'employee') else 'catalog')
        return render(request, 'login.html', {'error': True})

    return render(request, 'login.html', {})


def logout_view(request):
    logout(request)
    return redirect('login')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        errors = {}
        if not username:
            errors['username'] = 'Username is required.'
        elif User.objects.filter(username=username).exists():
            errors['username'] = 'That username is already taken.'
        if not password1:
            errors['password1'] = 'Password is required.'
        elif len(password1) < 8:
            errors['password1'] = 'Password must be at least 8 characters.'
        elif password1 != password2:
            errors['password2'] = 'Passwords do not match.'

        if errors:
            return render(request, 'register.html', {'errors': errors, 'old': request.POST})

        user = User.objects.create_user(username=username, email=email, password=password1)
        # Signal auto-creates UserProfile with role='user'
        login(request, user)
        messages.info(request, 'Account created. You have read-only access until an admin upgrades your role.')
        return redirect('catalog')

    return render(request, 'register.html', {})


# ---------------------------------------------------------------------------
# Dashboard (employee + admin)
# ---------------------------------------------------------------------------

@employee_required
def dashboard_view(request):
    today = timezone.localdate()

    total_items = Item.objects.count()
    low_stock_items = Item.objects.filter(status__in=['low_stock', 'out_of_stock']).order_by('quantity')

    today_sales = Sale.objects.filter(created_at__date=today)
    today_revenue = sum(s.total_revenue for s in today_sales) or Decimal('0.00')
    today_profit = sum(s.total_profit for s in today_sales) or Decimal('0.00')

    recent_sales = Sale.objects.prefetch_related('items__item').order_by('-created_at')[:10]

    # Chart: last 7 days revenue
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_sales = Sale.objects.filter(created_at__date=day)
        day_revenue = float(sum(s.total_revenue for s in day_sales) or 0)
        chart_labels.append(day.strftime('%b %d'))
        chart_data.append(day_revenue)

    context = {
        'today': today,
        'total_items': total_items,
        'low_stock_count': low_stock_items.count(),
        'low_stock_items': low_stock_items,
        'today_revenue': today_revenue,
        'today_profit': today_profit,
        'recent_sales': recent_sales,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
    }
    return render(request, 'dashboard.html', context)


# ---------------------------------------------------------------------------
# Catalog (read-only, role=user)
# ---------------------------------------------------------------------------

@login_required
def catalog_view(request):
    role = _get_role(request.user)
    if role in ('admin', 'employee'):
        return redirect('dashboard')

    items = Item.objects.all().order_by('category', 'name')
    return render(request, 'catalog.html', {'items': items})


# ---------------------------------------------------------------------------
# Inventory management (employee + admin)
# ---------------------------------------------------------------------------

@employee_required
def items_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            name = request.POST.get('name', '').strip()
            category = request.POST.get('category', '').strip()
            try:
                quantity = int(request.POST.get('quantity', 0))
                reorder_level = int(request.POST.get('reorder_level', 5))
                purchase_price = Decimal(request.POST.get('purchase_price', '0'))
            except (ValueError, InvalidOperation):
                messages.error(request, 'Invalid numeric values.')
                return redirect('items')
            currency = request.POST.get('currency', 'GEL')
            if not name or not category:
                messages.error(request, 'Name and category are required.')
                return redirect('items')
            item = Item(name=name, category=category, quantity=quantity,
                        reorder_level=reorder_level, purchase_price=purchase_price,
                        currency=currency)
            item.save()
            log_activity(request.user, 'Added item', f'{item.name} [{item.sku}]')
            messages.success(request, f'Item "{item.name}" added.')

        elif action == 'edit':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(Item, pk=item_id)
            item.name = request.POST.get('name', item.name).strip()
            item.category = request.POST.get('category', item.category).strip()
            try:
                item.quantity = int(request.POST.get('quantity', item.quantity))
                item.reorder_level = int(request.POST.get('reorder_level', item.reorder_level))
                item.purchase_price = Decimal(request.POST.get('purchase_price', item.purchase_price))
            except (ValueError, InvalidOperation):
                messages.error(request, 'Invalid numeric values.')
                return redirect('items')
            item.currency = request.POST.get('currency', item.currency)
            item.save()
            log_activity(request.user, 'Edited item', f'{item.name} [{item.sku}]')
            messages.success(request, f'Item "{item.name}" updated.')

        elif action == 'delete':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(Item, pk=item_id)
            name = item.name
            item.delete()
            log_activity(request.user, 'Deleted item', name)
            messages.success(request, f'Item "{name}" deleted.')

        return redirect('items')

    items = Item.objects.all().order_by('category', 'name')
    return render(request, 'inventory/list.html', {'items': items})


# ---------------------------------------------------------------------------
# Sales (employee + admin)
# ---------------------------------------------------------------------------

@employee_required
def sales_list_view(request):
    sales = Sale.objects.prefetch_related('items__item').order_by('-created_at')
    return render(request, 'sales/list.html', {'sales': sales})


@employee_required
@transaction.atomic
def sale_new_view(request):
    if request.method == 'POST':
        buyer_name = request.POST.get('buyer_name', '').strip()
        currency = request.POST.get('currency', 'GEL')
        item_ids = request.POST.getlist('item_id')
        quantities = request.POST.getlist('quantity')
        sale_prices = request.POST.getlist('sale_price')

        errors = []
        lines = []
        for item_id, qty_str, price_str in zip(item_ids, quantities, sale_prices):
            if not item_id:
                continue
            try:
                item = Item.objects.get(pk=item_id)
                qty = int(qty_str)
                price = Decimal(price_str)
            except (Item.DoesNotExist, ValueError, InvalidOperation):
                errors.append(f'Invalid data for one of the items.')
                continue
            if qty < 1:
                errors.append(f'Quantity must be at least 1 for {item.name}.')
            elif item.quantity < qty:
                errors.append(f'Only {item.quantity} units of "{item.name}" in stock.')
            else:
                lines.append((item, qty, price))

        if errors:
            for e in errors:
                messages.error(request, e)
            items = Item.objects.filter(quantity__gt=0).order_by('name')
            return render(request, 'sales/new.html', {'items': items, 'post': request.POST})

        if not lines:
            messages.error(request, 'Add at least one item to the sale.')
            items = Item.objects.filter(quantity__gt=0).order_by('name')
            return render(request, 'sales/new.html', {'items': items})

        sale = Sale.objects.create(buyer_name=buyer_name, currency=currency)
        for item, qty, price in lines:
            SaleItem.objects.create(
                sale=sale, item=item, quantity=qty,
                sale_price=price, cost_price=item.purchase_price,
            )
            item.quantity -= qty
            item.save()

        sale.calculate_totals()
        sale.save()
        log_activity(request.user, 'Recorded sale',
                     f'Sale #{sale.pk} — {sale.buyer_name or "Anonymous"} '
                     f'{sale.currency} {sale.total_revenue}')
        messages.success(request, f'Sale #{sale.pk} recorded. Revenue: {sale.currency} {sale.total_revenue}')
        return redirect('sales_list')

    items = Item.objects.filter(quantity__gt=0).order_by('name')
    return render(request, 'sales/new.html', {'items': items})


@employee_required
@transaction.atomic
def sale_delete_view(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == 'POST':
        for line in sale.items.select_related('item').all():
            line.item.quantity += line.quantity
            line.item.save()
        detail = f'Sale #{sale.pk} — {sale.buyer_name or "Anonymous"}'
        sale.delete()
        log_activity(request.user, 'Deleted sale', detail)
        messages.success(request, f'Sale #{pk} deleted and stock restored.')
    return redirect('sales_list')


# ---------------------------------------------------------------------------
# User management (admin only)
# ---------------------------------------------------------------------------

@admin_required
def users_view(request):
    users = User.objects.select_related('profile').order_by('date_joined')
    return render(request, 'users/list.html', {'users': users})


@admin_required
def user_role_view(request, pk):
    if request.method == 'POST':
        target = get_object_or_404(User, pk=pk)
        new_role = request.POST.get('role')
        if new_role not in ('admin', 'employee', 'user'):
            messages.error(request, 'Invalid role.')
            return redirect('users')
        profile, _ = UserProfile.objects.get_or_create(user=target)
        old_role = profile.role
        profile.role = new_role
        profile.save()
        log_activity(request.user, 'Changed role',
                     f'{target.username}: {old_role} → {new_role}')
        messages.success(request, f'{target.username} is now {new_role}.')
    return redirect('users')


@admin_required
def user_toggle_view(request, pk):
    if request.method == 'POST':
        target = get_object_or_404(User, pk=pk)
        if target == request.user:
            messages.error(request, 'You cannot deactivate your own account.')
            return redirect('users')
        target.is_active = not target.is_active
        target.save()
        status = 'activated' if target.is_active else 'deactivated'
        log_activity(request.user, f'User {status}', target.username)
        messages.success(request, f'{target.username} has been {status}.')
    return redirect('users')


@admin_required
def user_reset_password_view(request, pk):
    if request.method == 'POST':
        target = get_object_or_404(User, pk=pk)
        new_password = request.POST.get('new_password', '')
        confirm = request.POST.get('confirm_password', '')

        if len(new_password) < 8:
            messages.error(request, f'Password for {target.username} must be at least 8 characters.')
            return redirect('users')
        if new_password != confirm:
            messages.error(request, 'Passwords do not match.')
            return redirect('users')

        target.set_password(new_password)
        target.save()
        log_activity(request.user, 'Reset password', target.username)
        messages.success(request, f'Password for {target.username} has been reset.')
    return redirect('users')


# ---------------------------------------------------------------------------
# Activity log (admin only)
# ---------------------------------------------------------------------------

@admin_required
def activity_view(request):
    from apps.accounts.models import ActivityLog
    logs = ActivityLog.objects.select_related('user').all()[:200]
    return render(request, 'activity/list.html', {'logs': logs})
