import json
from decimal import Decimal
from datetime import date, timedelta
import calendar

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Max, F, Q
from django.db.models.functions import TruncMonth, TruncDay, Coalesce
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import UserCreationForm

from .models import Expense, Category, Budget, CashBalance, BorrowedMoney, Repayment, LentMoney, LentRepayment
from .forms import ExpenseForm, BudgetForm, CashBalanceForm, ExpenseFilterForm, BorrowedMoneyForm, RepaymentForm, LentMoneyForm, LentRepaymentForm


# ─── helpers ────────────────────────────────────────────────────────────────

def _get_cash_balance(user):
    return CashBalance.get_balance(user)


def _get_current_budget(user):
    today = date.today()
    first_of_month = today.replace(day=1)
    try:
        return Budget.objects.get(user=user, month=first_of_month)
    except Budget.DoesNotExist:
        return None


def _month_spent(user, year=None, month=None):
    today = date.today()
    year = year or today.year
    month = month or today.month
    result = Expense.objects.filter(
        user=user, date__year=year, date__month=month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    return result


# ─── Dashboard ──────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    # Auto-adopt existing orphan data for the first logged-in user
    if not CashBalance.objects.filter(user=request.user).exists():
        orphan_bal = CashBalance.objects.filter(user__isnull=True).first()
        if orphan_bal:
            # Check if there is a primary key collision with an existing user's balance
            try:
                orphan_bal.user = request.user
                orphan_bal.save()
            except Exception:
                # If there's an integrity conflict, merge/delete safely
                CashBalance.objects.filter(user__isnull=True).delete()

    Expense.objects.filter(user__isnull=True).update(user=request.user)
    Budget.objects.filter(user__isnull=True).update(user=request.user)
    Category.objects.filter(user__isnull=True, is_default=False).update(user=request.user)

    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    today_total = Expense.objects.filter(user=request.user, date=today).aggregate(
        total=Sum('amount'))['total'] or Decimal('0.00')
    week_total = Expense.objects.filter(user=request.user, date__gte=week_start).aggregate(
        total=Sum('amount'))['total'] or Decimal('0.00')
    month_total = _month_spent(request.user)
    all_total = Expense.objects.filter(user=request.user).aggregate(
        total=Sum('amount'))['total'] or Decimal('0.00')

    # ── Cash remaining ──
    cash_balance = _get_cash_balance(request.user)
    remaining_cash = cash_balance.balance - all_total

    # ── Expense counts ──
    total_count = Expense.objects.filter(user=request.user).count()
    today_count = Expense.objects.filter(user=request.user, date=today).count()

    # ── Recent expenses ──
    recent_expenses = Expense.objects.filter(user=request.user).select_related('category').order_by('-date', '-created_at')[:8]

    # ── Last expense ──
    last_expense = Expense.objects.filter(user=request.user).select_related('category').order_by('-created_at').first()

    # ── Spending trend vs last month ──
    first_of_month = today.replace(day=1)
    if first_of_month.month == 1:
        last_month_first = first_of_month.replace(year=first_of_month.year - 1, month=12)
    else:
        last_month_first = first_of_month.replace(month=first_of_month.month - 1)
    last_month_total = _month_spent(request.user, year=last_month_first.year, month=last_month_first.month)
    if last_month_total > 0:
        trend_pct = int(((month_total - last_month_total) / last_month_total) * 100)
    else:
        trend_pct = None

    # ── Days left in month ──
    _, days_in_month = calendar.monthrange(today.year, today.month)
    days_left = days_in_month - today.day
    # Projected month total based on daily average so far
    days_passed = today.day
    projected_month = round((month_total / days_passed) * days_in_month, 2) if days_passed > 0 and month_total > 0 else Decimal('0.00')

    # ── Budget ──
    current_budget = _get_current_budget(request.user)
    budget_percent = None
    budget_remaining = None
    budget_warning = False
    if current_budget and current_budget.amount > 0:
        budget_percent = int((month_total / current_budget.amount) * 100)
        budget_remaining = current_budget.amount - month_total
        budget_warning = budget_percent >= 80

    # ── Category breakdown for mini-chart (current month) ──
    cat_data = (
        Expense.objects.filter(user=request.user, date__year=today.year, date__month=today.month)
        .values('category__name', 'category__color', 'category__icon')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:5]
    )

    # ── Top category all time ──
    top_category = (
        Expense.objects.filter(user=request.user).values('category__name', 'category__icon', 'category__color')
        .annotate(total=Sum('amount'))
        .order_by('-total')
        .first()
    )

    context = {
        'today_total': today_total,
        'week_total': week_total,
        'month_total': month_total,
        'all_total': all_total,
        'remaining_cash': remaining_cash,
        'cash_balance': cash_balance,
        'total_count': total_count,
        'today_count': today_count,
        'recent_expenses': recent_expenses,
        'last_expense': last_expense,
        'trend_pct': trend_pct,
        'last_month_total': last_month_total,
        'days_left': days_left,
        'days_in_month': days_in_month,
        'projected_month': projected_month,
        'current_budget': current_budget,
        'budget_percent': budget_percent,
        'budget_remaining': budget_remaining,
        'budget_warning': budget_warning,
        'cat_data': list(cat_data),
        'top_category': top_category,
        'today': today,
        'active_page': 'dashboard',
        'global_remaining_cash': remaining_cash,
    }
    return render(request, 'expenses/dashboard.html', context)


# ─── Expense CRUD ────────────────────────────────────────────────────────────

@login_required
def expense_list(request):
    form = ExpenseFilterForm(request.GET, user=request.user)
    expenses = Expense.objects.filter(user=request.user).select_related('category').all()

    if form.is_valid():
        search = form.cleaned_data.get('search')
        category = form.cleaned_data.get('category')
        payment_method = form.cleaned_data.get('payment_method')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        sort = form.cleaned_data.get('sort') or '-date'

        if search:
            expenses = expenses.filter(title__icontains=search)
        if category:
            expenses = expenses.filter(category=category)
        if payment_method:
            expenses = expenses.filter(payment_method=payment_method)
        if date_from:
            expenses = expenses.filter(date__gte=date_from)
        if date_to:
            expenses = expenses.filter(date__lte=date_to)
        expenses = expenses.order_by(sort)
    else:
        expenses = expenses.order_by('-date', '-created_at')

    total_filtered = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    context = {
        'expenses': expenses,
        'form': form,
        'total_filtered': total_filtered,
        'active_page': 'expenses',
    }
    return render(request, 'expenses/expense_list.html', context)


@login_required
def expense_add(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            messages.success(request, 'Expense added successfully!')
            return redirect('expense_list')
    else:
        form = ExpenseForm(initial={'date': date.today()}, user=request.user)

    context = {
        'form': form,
        'action': 'Add',
        'active_page': 'expenses',
    }
    return render(request, 'expenses/expense_form.html', context)


@login_required
def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated successfully!')
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense, user=request.user)

    context = {
        'form': form,
        'expense': expense,
        'action': 'Edit',
        'active_page': 'expenses',
    }
    return render(request, 'expenses/expense_form.html', context)


@login_required
def expense_detail(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    context = {
        'expense': expense,
        'active_page': 'expenses',
    }
    return render(request, 'expenses/expense_detail.html', context)


@login_required
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        expense.delete()
        messages.success(request, f'"{expense.title}" deleted successfully.')
        return redirect('expense_list')

    context = {
        'expense': expense,
        'active_page': 'expenses',
    }
    return render(request, 'expenses/expense_confirm_delete.html', context)


# ─── Cash Management ─────────────────────────────────────────────────────────

@login_required
def cash_management(request):
    cash_balance = _get_cash_balance(request.user)
    total_spent = Expense.objects.filter(user=request.user).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    remaining = cash_balance.balance - total_spent

    if request.method == 'POST':
        form = CashBalanceForm(request.POST, instance=cash_balance)
        if form.is_valid():
            balance = form.save(commit=False)
            balance.user = request.user
            balance.save()
            messages.success(request, 'Cash balance updated!')
            return redirect('cash_management')
    else:
        form = CashBalanceForm(instance=cash_balance)

    context = {
        'form': form,
        'cash_balance': cash_balance,
        'total_spent': total_spent,
        'remaining': remaining,
        'active_page': 'cash',
    }
    return render(request, 'expenses/cash_management.html', context)


# ─── Budget ──────────────────────────────────────────────────────────────────

@login_required
def budget_view(request):
    today = date.today()
    first_of_month = today.replace(day=1)
    current_budget = _get_current_budget(request.user)
    month_spent = _month_spent(request.user)

    budget_percent = None
    budget_remaining = None
    budget_warning = False
    if current_budget and current_budget.amount > 0:
        budget_percent = min(int((month_spent / current_budget.amount) * 100), 100)
        budget_remaining = current_budget.amount - month_spent
        budget_warning = budget_percent >= 80

    all_budgets = Budget.objects.filter(user=request.user).order_by('-month')[:12]

    if request.method == 'POST':
        instance = current_budget
        form = BudgetForm(request.POST, instance=instance, user=request.user)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            budget.save()
            messages.success(request, 'Budget saved!')
            return redirect('budget')
    else:
        initial = {'month': first_of_month.strftime('%Y-%m-%d')}
        form = BudgetForm(instance=current_budget, initial=initial if not current_budget else {}, user=request.user)

    context = {
        'form': form,
        'current_budget': current_budget,
        'month_spent': month_spent,
        'budget_percent': budget_percent,
        'budget_remaining': budget_remaining,
        'budget_warning': budget_warning,
        'all_budgets': all_budgets,
        'today': today,
        'active_page': 'budget',
    }
    return render(request, 'expenses/budget.html', context)


# ─── Reports ─────────────────────────────────────────────────────────────────

@login_required
def reports(request):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    first_of_month = today.replace(day=1)

    # Summary totals
    daily_total = Expense.objects.filter(user=request.user, date=today).aggregate(
        total=Sum('amount'))['total'] or Decimal('0.00')
    weekly_total = Expense.objects.filter(user=request.user, date__gte=week_start).aggregate(
        total=Sum('amount'))['total'] or Decimal('0.00')
    monthly_total = _month_spent(request.user)

    # Category breakdown (current month)
    cat_breakdown = (
        Expense.objects.filter(user=request.user, date__year=today.year, date__month=today.month)
        .values('category__name', 'category__color', 'category__icon')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )

    # All-time category breakdown
    cat_all = (
        Expense.objects.filter(user=request.user).values('category__name', 'category__color', 'category__icon')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    # Highest spending category
    highest_cat = cat_all.first()

    # Highest spending day (all time)
    day_totals = (
        Expense.objects.filter(user=request.user).values('date')
        .annotate(total=Sum('amount'))
        .order_by('-total')
        .first()
    )

    # Average daily spending (last 30 days)
    thirty_days_ago = today - timedelta(days=30)
    avg_data = Expense.objects.filter(user=request.user, date__gte=thirty_days_ago).aggregate(
        total=Sum('amount'))['total'] or Decimal('0.00')
    avg_daily = round(avg_data / 30, 2)

    # Monthly history (last 6 months)
    monthly_history = (
        Expense.objects.filter(user=request.user).annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('-month')[:6]
    )

    # Daily (last 7 days)
    daily_history = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        total = Expense.objects.filter(user=request.user, date=d).aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')
        daily_history.append({'date': d.strftime('%a'), 'total': float(total)})

    context = {
        'daily_total': daily_total,
        'weekly_total': weekly_total,
        'monthly_total': monthly_total,
        'cat_breakdown': list(cat_breakdown),
        'cat_all': list(cat_all),
        'highest_cat': highest_cat,
        'day_totals': day_totals,
        'avg_daily': avg_daily,
        'monthly_history': list(monthly_history),
        'daily_history': daily_history,
        'today': today,
        'active_page': 'reports',
    }
    return render(request, 'expenses/reports.html', context)


# ─── Charts JSON API ─────────────────────────────────────────────────────────

@login_required
def charts_data(request):
    today = date.today()

    # Category-wise (current month)
    cat_data = list(
        Expense.objects.filter(user=request.user, date__year=today.year, date__month=today.month)
        .values('category__name', 'category__color')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    # Monthly spending (last 6 months)
    monthly_raw = (
        Expense.objects.filter(user=request.user).annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    monthly_labels = [r['month'].strftime('%b %Y') for r in monthly_raw]
    monthly_values = [float(r['total']) for r in monthly_raw]

    # Daily (last 14 days)
    daily_labels = []
    daily_values = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        total = Expense.objects.filter(user=request.user, date=d).aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')
        daily_labels.append(d.strftime('%d %b'))
        daily_values.append(float(total))

    return JsonResponse({
        'category': {
            'labels': [r['category__name'] or 'Uncategorised' for r in cat_data],
            'data': [float(r['total']) for r in cat_data],
            'colors': [r['category__color'] or '#AEB6BF' for r in cat_data],
        },
        'monthly': {
            'labels': monthly_labels,
            'data': monthly_values,
        },
        'daily': {
            'labels': daily_labels,
            'data': daily_values,
        },
    })


# ─── Authentication Views ───────────────────────────────────────────────────

def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, f"Welcome to CashTrack, {user.username}!")
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'expenses/signup.html', {'form': form})


def logout_view(request):
    auth_logout(request)
    messages.success(request, "You have logged out successfully.")
    return redirect('login')


# ─── Money Borrowed Views ────────────────────────────────────────────────────

@login_required
def borrowed_list(request):
    # Base queryset for current user
    loans = BorrowedMoney.objects.filter(user=request.user).annotate(
        total_repaid_annotated=Coalesce(Sum('repayments__amount_paid'), Decimal('0.00'))
    )

    # Search & filters
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    overdue_only = request.GET.get('overdue', '').strip()
    sort_by = request.GET.get('sort', '-date_received').strip()

    if search_query:
        loans = loans.filter(person_name__icontains=search_query)

    if date_from:
        loans = loans.filter(date_received__gte=date_from)
    if date_to:
        loans = loans.filter(date_received__lte=date_to)

    if overdue_only == 'true' or overdue_only == 'on':
        loans = loans.filter(total_repaid_annotated__lt=F('amount'), expected_return_date__lt=date.today())

    # Filter status
    # Pending: total_repaid_annotated == 0
    # Partially Paid: total_repaid_annotated > 0 and < amount
    # Paid: total_repaid_annotated == amount
    # Overdue: total_repaid_annotated < amount and expected_return_date < today
    if status_filter == 'pending':
        loans = loans.filter(total_repaid_annotated=0)
    elif status_filter == 'partially_paid':
        loans = loans.filter(total_repaid_annotated__gt=0, total_repaid_annotated__lt=F('amount'))
    elif status_filter == 'paid':
        loans = loans.filter(total_repaid_annotated=F('amount'))
    elif status_filter == 'overdue':
        loans = loans.filter(total_repaid_annotated__lt=F('amount'), expected_return_date__lt=date.today())

    # Sorting
    if sort_by in ['amount', '-amount', 'expected_return_date', '-expected_return_date', 'date_received', '-date_received']:
        loans = loans.order_by(sort_by)
    else:
        loans = loans.order_by('-date_received')

    # Aggregated Summary Stats for the User
    all_loans = BorrowedMoney.objects.filter(user=request.user).annotate(
        total_repaid_annotated=Coalesce(Sum('repayments__amount_paid'), Decimal('0.00'))
    )
    total_borrowed = all_loans.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_repaid = Repayment.objects.filter(borrowed_money__user=request.user).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
    remaining = max(Decimal('0.00'), total_borrowed - total_repaid)
    active_loans = all_loans.filter(total_repaid_annotated__lt=F('amount')).count()

    # Notifications & Reminders
    three_days_from_now = date.today() + timedelta(days=3)
    # Approaching loans (due in next 3 days, including today, but not overdue)
    approaching_loans = all_loans.filter(
        expected_return_date__gte=date.today(),
        expected_return_date__lte=three_days_from_now,
        total_repaid_annotated__lt=F('amount')
    )
    # Overdue loans
    overdue_loans = all_loans.filter(
        expected_return_date__lt=date.today(),
        total_repaid_annotated__lt=F('amount')
    )

    repayment_form = RepaymentForm()

    context = {
        'active_page': 'borrowed',
        'loans': loans,
        'total_borrowed': total_borrowed,
        'total_repaid': total_repaid,
        'remaining': remaining,
        'active_loans': active_loans,
        'approaching_loans': approaching_loans,
        'overdue_loans': overdue_loans,
        'repayment_form': repayment_form,
        'search_query': search_query,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'overdue_only': overdue_only,
        'sort_by': sort_by,
        'today': date.today(),
    }
    return render(request, 'expenses/borrowed_list.html', context)


@login_required
def borrowed_add(request):
    if request.method == 'POST':
        form = BorrowedMoneyForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.user = request.user
            loan.save()
            messages.success(request, f"Borrowed money record of ₹{loan.amount} from {loan.person_name} added successfully.")
            return redirect('borrowed_list')
    else:
        form = BorrowedMoneyForm()
    return render(request, 'expenses/borrowed_form.html', {'form': form, 'title': 'Add Borrowed Money', 'active_page': 'borrowed'})


@login_required
def borrowed_edit(request, pk):
    loan = get_object_or_404(BorrowedMoney, pk=pk, user=request.user)
    if request.method == 'POST':
        form = BorrowedMoneyForm(request.POST, instance=loan)
        if form.is_valid():
            form.save()
            messages.success(request, f"Borrowed money record from {loan.person_name} updated successfully.")
            return redirect('borrowed_list')
    else:
        form = BorrowedMoneyForm(instance=loan)
    return render(request, 'expenses/borrowed_form.html', {'form': form, 'title': 'Edit Borrowed Money', 'active_page': 'borrowed', 'loan': loan})


@login_required
def borrowed_delete(request, pk):
    loan = get_object_or_404(BorrowedMoney, pk=pk, user=request.user)
    if request.method == 'POST':
        person_name = loan.person_name
        amount = loan.amount
        loan.delete()
        messages.success(request, f"Borrowed money record of ₹{amount} from {person_name} deleted successfully.")
        return redirect('borrowed_list')
    return render(request, 'expenses/borrowed_confirm_delete.html', {'loan': loan, 'active_page': 'borrowed'})


@login_required
def borrowed_repay(request, pk):
    loan = get_object_or_404(BorrowedMoney, pk=pk, user=request.user)
    if request.method == 'POST':
        form = RepaymentForm(request.POST, borrowed_money=loan)
        if form.is_valid():
            repayment = form.save(commit=False)
            repayment.borrowed_money = loan
            
            if form.cleaned_data.get('record_as_expense'):
                category = Category.objects.filter(user=request.user, name='Other').first() or \
                           Category.objects.filter(user__isnull=True, name='Other').first()
                
                expense = Expense.objects.create(
                    user=request.user,
                    title=f"Repayment to {loan.person_name}",
                    amount=repayment.amount_paid,
                    date=repayment.payment_date,
                    description=repayment.notes or f"Repayment for borrowing: {loan.purpose}",
                    payment_method='upi',
                    category=category
                )
                repayment.expense = expense
            
            repayment.save()
            messages.success(request, f"Repayment of ₹{repayment.amount_paid} recorded successfully.")
            return redirect('borrowed_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error: {error}")
    return redirect('borrowed_list')


@login_required
def borrowed_person_detail(request, person_name):
    loans = BorrowedMoney.objects.filter(user=request.user, person_name__iexact=person_name).order_by('-date_received')
    if not loans.exists():
        messages.error(request, f"No borrowing records found for person: {person_name}")
        return redirect('borrowed_list')

    repayments = Repayment.objects.filter(
        borrowed_money__user=request.user, 
        borrowed_money__person_name__iexact=person_name
    ).order_by('-payment_date', '-created_at')

    total_borrowed = loans.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_repaid = repayments.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
    remaining = max(Decimal('0.00'), total_borrowed - total_repaid)

    context = {
        'active_page': 'borrowed',
        'person_name': person_name,
        'loans': loans,
        'repayments': repayments,
        'total_borrowed': total_borrowed,
        'total_repaid': total_repaid,
        'remaining': remaining,
    }
    return render(request, 'expenses/borrowed_person.html', context)


@login_required
def repayment_delete(request, pk):
    repayment = get_object_or_404(Repayment, pk=pk, borrowed_money__user=request.user)
    person_name = repayment.borrowed_money.person_name
    repayment.delete()
    messages.success(request, "Repayment deleted successfully.")
    return redirect('borrowed_person_detail', person_name=person_name)


@login_required
def api_borrowed_charts(request):
    loans = BorrowedMoney.objects.filter(user=request.user)
    total_borrowed = loans.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_repaid = Repayment.objects.filter(borrowed_money__user=request.user).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
    remaining = max(Decimal('0.00'), total_borrowed - total_repaid)

    today = date.today()
    months = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        months.append((y, m))

    labels = []
    borrowed_data = []
    repaid_data = []
    for y, m in months:
        month_name = date(y, m, 1).strftime('%b %Y')
        labels.append(month_name)

        borrowed_sum = BorrowedMoney.objects.filter(
            user=request.user,
            date_received__year=y,
            date_received__month=m
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        borrowed_data.append(float(borrowed_sum))

        repaid_sum = Repayment.objects.filter(
            borrowed_money__user=request.user,
            payment_date__year=y,
            payment_date__month=m
        ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
        repaid_data.append(float(repaid_sum))

    return JsonResponse({
        'summary': {
            'labels': ['Total Repaid', 'Remaining Balance'],
            'data': [float(total_repaid), float(remaining)],
            'colors': ['#3fb950', '#f85149'] if remaining > 0 else ['#3fb950', '#21262d']
        },
        'monthly': {
            'labels': labels,
            'borrowed': borrowed_data,
            'repaid': repaid_data
        }
    })


# ─── Money Lent Views ────────────────────────────────────────────────────────

@login_required
def lent_list(request):
    loans = LentMoney.objects.filter(user=request.user).annotate(
        total_repaid_annotated=Coalesce(Sum('repayments__amount_received'), Decimal('0.00'))
    )

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    overdue_only = request.GET.get('overdue', '').strip()
    sort_by = request.GET.get('sort', '-date_lent').strip()

    if search_query:
        loans = loans.filter(person_name__icontains=search_query)

    if date_from:
        loans = loans.filter(date_lent__gte=date_from)
    if date_to:
        loans = loans.filter(date_lent__lte=date_to)

    if overdue_only == 'true' or overdue_only == 'on':
        loans = loans.filter(total_repaid_annotated__lt=F('amount'), expected_return_date__lt=date.today())

    if status_filter == 'pending':
        loans = loans.filter(total_repaid_annotated=0)
    elif status_filter == 'partially_paid':
        loans = loans.filter(total_repaid_annotated__gt=0, total_repaid_annotated__lt=F('amount'))
    elif status_filter == 'paid':
        loans = loans.filter(total_repaid_annotated=F('amount'))
    elif status_filter == 'overdue':
        loans = loans.filter(total_repaid_annotated__lt=F('amount'), expected_return_date__lt=date.today())

    if sort_by in ['amount', '-amount', 'expected_return_date', '-expected_return_date', 'date_lent', '-date_lent']:
        loans = loans.order_by(sort_by)
    else:
        loans = loans.order_by('-date_lent')

    all_loans = LentMoney.objects.filter(user=request.user).annotate(
        total_repaid_annotated=Coalesce(Sum('repayments__amount_received'), Decimal('0.00'))
    )
    total_lent = all_loans.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_repaid = LentRepayment.objects.filter(lent_money__user=request.user).aggregate(total=Sum('amount_received'))['total'] or Decimal('0.00')
    remaining = max(Decimal('0.00'), total_lent - total_repaid)
    active_loans = all_loans.filter(total_repaid_annotated__lt=F('amount')).count()

    three_days_from_now = date.today() + timedelta(days=3)
    approaching_loans = all_loans.filter(
        expected_return_date__gte=date.today(),
        expected_return_date__lte=three_days_from_now,
        total_repaid_annotated__lt=F('amount')
    )
    overdue_loans = all_loans.filter(
        expected_return_date__lt=date.today(),
        total_repaid_annotated__lt=F('amount')
    )

    repayment_form = LentRepaymentForm()

    context = {
        'active_page': 'lent',
        'loans': loans,
        'total_lent': total_lent,
        'total_repaid': total_repaid,
        'remaining': remaining,
        'active_loans': active_loans,
        'approaching_loans': approaching_loans,
        'overdue_loans': overdue_loans,
        'repayment_form': repayment_form,
        'search_query': search_query,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'overdue_only': overdue_only,
        'sort_by': sort_by,
        'today': date.today(),
    }
    return render(request, 'expenses/lent_list.html', context)


@login_required
def lent_add(request):
    if request.method == 'POST':
        form = LentMoneyForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.user = request.user
            
            if form.cleaned_data.get('record_as_expense'):
                category = Category.objects.filter(user=request.user, name='Other').first() or \
                           Category.objects.filter(user__isnull=True, name='Other').first()
                
                expense = Expense.objects.create(
                    user=request.user,
                    title=f"Lent to {loan.person_name}",
                    amount=loan.amount,
                    date=loan.date_lent,
                    description=loan.notes or f"Lent money to {loan.person_name} for {loan.purpose}",
                    payment_method='upi',
                    category=category
                )
                loan.expense = expense

            loan.save()
            messages.success(request, f"Lent money record of ₹{loan.amount} to {loan.person_name} added successfully.")
            return redirect('lent_list')
    else:
        form = LentMoneyForm()
    return render(request, 'expenses/lent_form.html', {'form': form, 'title': 'Lend Money', 'active_page': 'lent'})


@login_required
def lent_edit(request, pk):
    loan = get_object_or_404(LentMoney, pk=pk, user=request.user)
    if request.method == 'POST':
        form = LentMoneyForm(request.POST, instance=loan)
        if form.is_valid():
            loan = form.save(commit=False)
            
            if form.cleaned_data.get('record_as_expense'):
                category = Category.objects.filter(user=request.user, name='Other').first() or \
                           Category.objects.filter(user__isnull=True, name='Other').first()
                if loan.expense:
                    loan.expense.amount = loan.amount
                    loan.expense.date = loan.date_lent
                    loan.expense.title = f"Lent to {loan.person_name}"
                    loan.expense.save()
                else:
                    expense = Expense.objects.create(
                        user=request.user,
                        title=f"Lent to {loan.person_name}",
                        amount=loan.amount,
                        date=loan.date_lent,
                        description=loan.notes or f"Lent money to {loan.person_name} for {loan.purpose}",
                        payment_method='upi',
                        category=category
                    )
                    loan.expense = expense
            else:
                if loan.expense:
                    loan.expense.delete()
                    loan.expense = None
            
            loan.save()
            messages.success(request, f"Lent money record to {loan.person_name} updated successfully.")
            return redirect('lent_list')
    else:
        form = LentMoneyForm(instance=loan)
    return render(request, 'expenses/lent_form.html', {'form': form, 'title': 'Edit Lent Money', 'active_page': 'lent', 'loan': loan})


@login_required
def lent_delete(request, pk):
    loan = get_object_or_404(LentMoney, pk=pk, user=request.user)
    if request.method == 'POST':
        person_name = loan.person_name
        amount = loan.amount
        loan.delete()
        messages.success(request, f"Lent money record of ₹{amount} to {person_name} deleted successfully.")
        return redirect('lent_list')
    return render(request, 'expenses/lent_confirm_delete.html', {'loan': loan, 'active_page': 'lent'})


@login_required
def lent_repay(request, pk):
    loan = get_object_or_404(LentMoney, pk=pk, user=request.user)
    if request.method == 'POST':
        form = LentRepaymentForm(request.POST, lent_money=loan)
        if form.is_valid():
            repayment = form.save(commit=False)
            repayment.lent_money = loan
            repayment.save()
            messages.success(request, f"Repayment of ₹{repayment.amount_received} from {loan.person_name} recorded successfully.")
            return redirect('lent_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error: {error}")
    return redirect('lent_list')


@login_required
def lent_person_detail(request, person_name):
    loans = LentMoney.objects.filter(user=request.user, person_name__iexact=person_name).order_by('-date_lent')
    if not loans.exists():
        messages.error(request, f"No lending records found for person: {person_name}")
        return redirect('lent_list')

    repayments = LentRepayment.objects.filter(
        lent_money__user=request.user, 
        lent_money__person_name__iexact=person_name
    ).order_by('-payment_date', '-created_at')

    total_lent = loans.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_repaid = repayments.aggregate(total=Sum('amount_received'))['total'] or Decimal('0.00')
    remaining = max(Decimal('0.00'), total_lent - total_repaid)

    context = {
        'active_page': 'lent',
        'person_name': person_name,
        'loans': loans,
        'repayments': repayments,
        'total_lent': total_lent,
        'total_repaid': total_repaid,
        'remaining': remaining,
    }
    return render(request, 'expenses/lent_person.html', context)


@login_required
def lent_repayment_delete(request, pk):
    repayment = get_object_or_404(LentRepayment, pk=pk, lent_money__user=request.user)
    person_name = repayment.lent_money.person_name
    repayment.delete()
    messages.success(request, "Repayment record deleted successfully.")
    return redirect('lent_person_detail', person_name=person_name)


@login_required
def api_lent_charts(request):
    loans = LentMoney.objects.filter(user=request.user)
    total_lent = loans.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_repaid = LentRepayment.objects.filter(lent_money__user=request.user).aggregate(total=Sum('amount_received'))['total'] or Decimal('0.00')
    remaining = max(Decimal('0.00'), total_lent - total_repaid)

    today = date.today()
    months = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        months.append((y, m))

    labels = []
    lent_data = []
    repaid_data = []
    for y, m in months:
        month_name = date(y, m, 1).strftime('%b %Y')
        labels.append(month_name)

        lent_sum = LentMoney.objects.filter(
            user=request.user,
            date_lent__year=y,
            date_lent__month=m
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        lent_data.append(float(lent_sum))

        repaid_sum = LentRepayment.objects.filter(
            lent_money__user=request.user,
            payment_date__year=y,
            payment_date__month=m
        ).aggregate(total=Sum('amount_received'))['total'] or Decimal('0.00')
        repaid_data.append(float(repaid_sum))

    return JsonResponse({
        'summary': {
            'labels': ['Total Received', 'Remaining Balance'],
            'data': [float(total_repaid), float(remaining)],
            'colors': ['#3fb950', '#f85149'] if remaining > 0 else ['#3fb950', '#21262d']
        },
        'monthly': {
            'labels': labels,
            'lent': lent_data,
            'repaid': repaid_data
        }
    })


