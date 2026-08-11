from django.contrib import admin
from .models import Category, Expense, Budget, CashBalance


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('icon', 'name', 'color', 'is_default', 'created_at')
    list_filter = ('is_default',)
    search_fields = ('name',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'amount', 'category', 'date', 'payment_method', 'created_at')
    list_filter = ('category', 'payment_method', 'date')
    search_fields = ('title', 'description')
    date_hierarchy = 'date'
    ordering = ('-date', '-created_at')


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('month', 'amount', 'created_at', 'updated_at')
    ordering = ('-month',)


@admin.register(CashBalance)
class CashBalanceAdmin(admin.ModelAdmin):
    list_display = ('balance', 'updated_at')
