from .models import CashBalance, Expense
from django.db.models import Sum
from decimal import Decimal


def cash_balance_context(request):
    """Make remaining cash available globally in all templates."""
    try:
        cash = CashBalance.get_balance(request.user)
        all_total = Expense.objects.aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
        remaining = cash.balance - all_total
        return {
            'global_cash_balance': cash,
            'global_all_total': all_total,
            'global_remaining_cash': remaining,
        }
    except Exception:
        return {}
