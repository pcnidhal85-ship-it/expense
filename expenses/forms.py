from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
import datetime
from .models import Expense, Budget, CashBalance, Category


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['title', 'amount', 'category', 'date', 'payment_method', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Lunch at restaurant',
                'id': 'id_title',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
                'id': 'id_amount',
            }),
            'category': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_category',
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'id': 'id_date',
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_payment_method',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Optional notes…',
                'rows': 3,
                'id': 'id_description',
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= Decimal('0'):
            raise ValidationError('Amount must be greater than zero.')
        return amount

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date > datetime.date.today():
            raise ValidationError('Expense date cannot be in the future.')
        return date


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['month', 'amount']
        widgets = {
            'month': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'month',
                'id': 'id_month',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '1',
                'id': 'id_budget_amount',
            }),
        }

    def clean_month(self):
        month = self.cleaned_data.get('month')
        if month:
            # Normalize to first day of month
            return month.replace(day=1)
        return month

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= Decimal('0'):
            raise ValidationError('Budget amount must be greater than zero.')
        return amount


class CashBalanceForm(forms.ModelForm):
    class Meta:
        model = CashBalance
        fields = ['balance']
        widgets = {
            'balance': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
                'id': 'id_balance',
            }),
        }

    def clean_balance(self):
        balance = self.cleaned_data.get('balance')
        if balance is not None and balance < Decimal('0'):
            raise ValidationError('Cash balance cannot be negative.')
        return balance


class ExpenseFilterForm(forms.Form):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search expenses…',
            'id': 'id_search',
        })
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label='All Categories',
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_filter_category',
        })
    )
    payment_method = forms.ChoiceField(
        choices=[('', 'All Methods')] + list(Expense.PAYMENT_METHOD_CHOICES),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_filter_payment',
        })
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'id_date_from',
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'id_date_to',
        })
    )
    sort = forms.ChoiceField(
        choices=[
            ('-date', 'Newest First'),
            ('date', 'Oldest First'),
            ('-amount', 'Highest Amount'),
            ('amount', 'Lowest Amount'),
        ],
        required=False,
        initial='-date',
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_sort',
        })
    )
