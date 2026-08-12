from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='expenses/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),

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
