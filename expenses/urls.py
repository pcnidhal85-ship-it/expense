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

    # Money Borrowed
    path('borrowed/', views.borrowed_list, name='borrowed_list'),
    path('borrowed/add/', views.borrowed_add, name='borrowed_add'),
    path('borrowed/<int:pk>/edit/', views.borrowed_edit, name='borrowed_edit'),
    path('borrowed/<int:pk>/delete/', views.borrowed_delete, name='borrowed_delete'),
    path('borrowed/<int:pk>/repay/', views.borrowed_repay, name='borrowed_repay'),
    path('borrowed/repayment/<int:pk>/delete/', views.repayment_delete, name='repayment_delete'),
    path('borrowed/person/<str:person_name>/', views.borrowed_person_detail, name='borrowed_person_detail'),
    path('api/borrowed/charts/', views.api_borrowed_charts, name='api_borrowed_charts'),

    # Money Lent
    path('lent/', views.lent_list, name='lent_list'),
    path('lent/add/', views.lent_add, name='lent_add'),
    path('lent/<int:pk>/edit/', views.lent_edit, name='lent_edit'),
    path('lent/<int:pk>/delete/', views.lent_delete, name='lent_delete'),
    path('lent/<int:pk>/repay/', views.lent_repay, name='lent_repay'),
    path('lent/repayment/<int:pk>/delete/', views.lent_repayment_delete, name='lent_repayment_delete'),
    path('lent/person/<str:person_name>/', views.lent_person_detail, name='lent_person_detail'),
    path('api/lent/charts/', views.api_lent_charts, name='api_lent_charts'),
]
