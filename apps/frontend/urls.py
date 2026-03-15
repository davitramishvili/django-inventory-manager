from django.shortcuts import redirect
from django.urls import path

from . import views

urlpatterns = [
    path('', lambda req: redirect('dashboard'), name='home'),

    # Auth
    path('login/',    views.login_view,    name='login'),
    path('logout/',   views.logout_view,   name='logout'),
    path('register/', views.register_view, name='register'),

    # Main pages
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('catalog/',   views.catalog_view,   name='catalog'),

    # Inventory
    path('inventory/', views.items_view, name='items'),

    # Sales
    path('sales/',               views.sales_list_view, name='sales_list'),
    path('sales/new/',           views.sale_new_view,   name='sale_new'),
    path('sales/<int:pk>/delete/', views.sale_delete_view, name='sale_delete'),

    # Users (admin only)
    path('users/',                      views.users_view,       name='users'),
    path('users/<int:pk>/role/',        views.user_role_view,   name='user_role'),
    path('users/<int:pk>/toggle/',         views.user_toggle_view,         name='user_toggle'),
    path('users/<int:pk>/reset-password/', views.user_reset_password_view, name='user_reset_password'),

    # Activity log (admin only)
    path('activity/', views.activity_view, name='activity'),
]
