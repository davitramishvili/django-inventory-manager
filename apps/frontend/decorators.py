from functools import wraps
from django.shortcuts import redirect


def _get_role(user):
    if user.is_superuser:
        return 'admin'
    try:
        return user.profile.role
    except Exception:
        return 'user'


def employee_required(view_func):
    """Allows admin and employee. Redirects plain users to /catalog/."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if _get_role(request.user) not in ('admin', 'employee'):
            return redirect('catalog')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Allows admin only. Redirects others to /dashboard/."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if _get_role(request.user) != 'admin':
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
