from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
import datetime
from .models import Expense, Budget, CashBalance, Category, BorrowedMoney, Repayment, LentMoney, LentRepayment


class ExpenseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_anonymous:
            from django.db.models import Q
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user) | Q(user__isnull=True)
            )
        else:
            self.fields['category'].queryset = Category.objects.filter(user__isnull=True)

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
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

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

    def clean(self):
        cleaned_data = super().clean()
        month = cleaned_data.get('month')
        if month and self.user:
            qs = Budget.objects.filter(user=self.user, month=month)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f"A budget for {month.strftime('%B %Y')} already exists.")
        return cleaned_data


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
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_anonymous:
            from django.db.models import Q
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user) | Q(user__isnull=True)
            )
        else:
            self.fields['category'].queryset = Category.objects.filter(user__isnull=True)

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


class BorrowedMoneyForm(forms.ModelForm):
    class Meta:
        model = BorrowedMoney
        fields = ['person_name', 'amount', 'date_received', 'purpose', 'expected_return_date', 'notes']
        widgets = {
            'person_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Rahul',
                'id': 'id_person_name',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
                'id': 'id_amount',
            }),
            'date_received': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'id': 'id_date_received',
            }),
            'purpose': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. College expenses',
                'id': 'id_purpose',
            }),
            'expected_return_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'id': 'id_expected_return_date',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Optional notes…',
                'rows': 3,
                'id': 'id_notes',
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= Decimal('0'):
            raise ValidationError('Amount must be greater than zero.')
        return amount

    def clean(self):
        cleaned_data = super().clean()
        date_received = cleaned_data.get('date_received')
        expected_return_date = cleaned_data.get('expected_return_date')
        if date_received and expected_return_date:
            if expected_return_date < date_received:
                raise ValidationError('Expected return date cannot be before the date received.')
        return cleaned_data


class RepaymentForm(forms.ModelForm):
    record_as_expense = forms.BooleanField(
        required=False,
        initial=True,
        label="Also record repayment as expense",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_record_as_expense'
        })
    )

    def __init__(self, *args, **kwargs):
        self.borrowed_money = kwargs.pop('borrowed_money', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.borrowed_money = self.instance.borrowed_money
            if self.instance.expense:
                self.fields['record_as_expense'].initial = True
            else:
                self.fields['record_as_expense'].initial = False

    class Meta:
        model = Repayment
        fields = ['amount_paid', 'payment_date', 'notes']
        widgets = {
            'amount_paid': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
                'id': 'id_amount_paid',
            }),
            'payment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'id': 'id_payment_date',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Optional notes…',
                'rows': 3,
                'id': 'id_repayment_notes',
            }),
        }

    def clean_amount_paid(self):
        amount = self.cleaned_data.get('amount_paid')
        if amount is not None and amount <= Decimal('0'):
            raise ValidationError('Repayment amount must be greater than zero.')
        
        if self.borrowed_money:
            remaining = self.borrowed_money.remaining_amount
            if self.instance and self.instance.pk:
                remaining += self.instance.amount_paid
            
            if amount > remaining:
                raise ValidationError(f'Repayment amount (₹{amount}) cannot exceed the remaining balance (₹{remaining}).')
        return amount


class LentMoneyForm(forms.ModelForm):
    record_as_expense = forms.BooleanField(
        required=False,
        initial=True,
        label="Also record lending as expense",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_record_as_expense'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.expense:
                self.fields['record_as_expense'].initial = True
            else:
                self.fields['record_as_expense'].initial = False

    class Meta:
        model = LentMoney
        fields = ['person_name', 'amount', 'date_lent', 'purpose', 'expected_return_date', 'notes']
        widgets = {
            'person_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Rahul',
                'id': 'id_person_name',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
                'id': 'id_amount',
            }),
            'date_lent': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'id': 'id_date_lent',
            }),
            'purpose': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Personal help',
                'id': 'id_purpose',
            }),
            'expected_return_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'id': 'id_expected_return_date',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Optional notes…',
                'rows': 3,
                'id': 'id_notes',
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= Decimal('0'):
            raise ValidationError('Amount must be greater than zero.')
        return amount

    def clean(self):
        cleaned_data = super().clean()
        date_lent = cleaned_data.get('date_lent')
        expected_return_date = cleaned_data.get('expected_return_date')
        if date_lent and expected_return_date:
            if expected_return_date < date_lent:
                raise ValidationError('Expected return date cannot be before the date lent.')
        return cleaned_data


class LentRepaymentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.lent_money = kwargs.pop('lent_money', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.lent_money = self.instance.lent_money

    class Meta:
        model = LentRepayment
        fields = ['amount_received', 'payment_date', 'notes']
        widgets = {
            'amount_received': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
                'id': 'id_amount_received',
            }),
            'payment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'id': 'id_payment_date',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Optional notes…',
                'rows': 3,
                'id': 'id_repayment_notes',
            }),
        }

    def clean_amount_received(self):
        amount = self.cleaned_data.get('amount_received')
        if amount is not None and amount <= Decimal('0'):
            raise ValidationError('Payment amount must be greater than zero.')
        
        if self.lent_money:
            remaining = self.lent_money.remaining_amount
            if self.instance and self.instance.pk:
                remaining += self.instance.amount_received
            
            if amount > remaining:
                raise ValidationError(f'Payment amount (₹{amount}) cannot exceed the remaining balance (₹{remaining}).')
        return amount


