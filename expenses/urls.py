from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Expenses
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.expense_add, name='expense_add'),
    path('expenses/<int:pk>/', views.expense_detail, name='expense_detail'),
    path('expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),

    # Cash Management
    path('cash/', views.cash_management, name='cash_management'),

    # Budget
    path('budget/', views.budget_view, name='budget'),

    # Reports
    path('reports/', views.reports, name='reports'),

    # Chart JSON API
    path('api/charts/', views.charts_data, name='charts_data'),
]
