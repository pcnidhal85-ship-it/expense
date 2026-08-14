from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import datetime


class Category(models.Model):
    ICON_CHOICES = [
        ('🍔', 'Food'),
        ('✈️', 'Travel'),
        ('🛍️', 'Shopping'),
        ('📋', 'Bills'),
        ('📚', 'Education'),
        ('🎬', 'Entertainment'),
        ('🏥', 'Health'),
        ('💻', 'Technology'),
        ('👤', 'Personal'),
        ('📦', 'Other'),
    ]

    COLOR_CHOICES = [
        ('#FF6B6B', 'Red'),
        ('#4ECDC4', 'Teal'),
        ('#45B7D1', 'Blue'),
        ('#96CEB4', 'Green'),
        ('#FFEAA7', 'Yellow'),
        ('#DDA0DD', 'Plum'),
        ('#98D8C8', 'Mint'),
        ('#F7DC6F', 'Gold'),
        ('#AEB6BF', 'Silver'),
        ('#F0A500', 'Orange'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='categories')
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, default='📦')
    color = models.CharField(max_length=7, default='#AEB6BF')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']
        unique_together = ('user', 'name')

    def __str__(self):
        return f"{self.icon} {self.name}"


class Expense(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('upi', 'UPI'),
        ('net_banking', 'Net Banking'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='expenses')
    title = models.CharField(max_length=200)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses'
    )
    date = models.DateField(default=datetime.date.today)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='upi'
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.title} — ₹{self.amount}"


class Budget(models.Model):
    """Monthly budget. One record per month per user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='budgets')
    month = models.DateField()  # stored as first day of the month
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1.00'))]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-month']
        unique_together = ('user', 'month')

    def __str__(self):
        return f"Budget for {self.month.strftime('%B %Y')}: ₹{self.amount}"


class CashBalance(models.Model):
    """Single-row pattern per user to track current cash balance."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='cash_balance')
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cash Balance'
        verbose_name_plural = 'Cash Balance'

    def __str__(self):
        username = self.user.username if self.user else "System"
        return f"{username}'s Cash Balance: ₹{self.balance}"

    @classmethod
    def get_balance(cls, user):
        if not user or user.is_anonymous:
            # Fallback for anonymous or unassigned data
            obj, _ = cls.objects.get_or_create(user=None, defaults={'balance': Decimal('0.00')})
            return obj
        obj, _ = cls.objects.get_or_create(user=user, defaults={'balance': Decimal('0.00')})
        return obj


class BorrowedMoney(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowed_money')
    person_name = models.CharField(max_length=150)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    date_received = models.DateField(default=datetime.date.today)
    purpose = models.CharField(max_length=255)
    expected_return_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_received', '-created_at']

    def __str__(self):
        return f"{self.person_name} — ₹{self.amount} ({self.purpose})"

    @property
    def total_repaid(self):
        return self.repayments.aggregate(total=models.Sum('amount_paid'))['total'] or Decimal('0.00')

    @property
    def remaining_amount(self):
        return max(Decimal('0.00'), self.amount - self.total_repaid)

    @property
    def days_left(self):
        if self.expected_return_date:
            delta = self.expected_return_date - datetime.date.today()
            return delta.days
        return None

    @property
    def calculated_status(self):
        remaining = self.remaining_amount
        if remaining == Decimal('0.00'):
            return 'Paid'
        if self.expected_return_date and self.expected_return_date < datetime.date.today():
            return 'Overdue'
        if remaining == self.amount:
            return 'Pending'
        return 'Partially Paid'



class Repayment(models.Model):
    borrowed_money = models.ForeignKey(BorrowedMoney, on_delete=models.CASCADE, related_name='repayments')
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_date = models.DateField(default=datetime.date.today)
    notes = models.TextField(blank=True, null=True)
    expense = models.OneToOneField(Expense, on_delete=models.SET_NULL, null=True, blank=True, related_name='repayment')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f"₹{self.amount_paid} repaid on {self.payment_date}"

    def save(self, *args, **kwargs):
        if self.expense:
            self.expense.amount = self.amount_paid
            self.expense.date = self.payment_date
            self.expense.title = f"Repayment to {self.borrowed_money.person_name}"
            self.expense.save()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.expense:
            self.expense.delete()
        super().delete(*args, **kwargs)


class LentMoney(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lent_money')
    person_name = models.CharField(max_length=150)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    date_lent = models.DateField(default=datetime.date.today)
    purpose = models.CharField(max_length=255)
    expected_return_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    expense = models.OneToOneField(Expense, on_delete=models.SET_NULL, null=True, blank=True, related_name='lent_record')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_lent', '-created_at']

    def __str__(self):
        return f"Lent to {self.person_name} — ₹{self.amount} ({self.purpose})"

    @property
    def total_repaid(self):
        return self.repayments.aggregate(total=models.Sum('amount_received'))['total'] or Decimal('0.00')

    @property
    def remaining_amount(self):
        return max(Decimal('0.00'), self.amount - self.total_repaid)

    @property
    def days_left(self):
        if self.expected_return_date:
            delta = self.expected_return_date - datetime.date.today()
            return delta.days
        return None

    @property
    def calculated_status(self):
        remaining = self.remaining_amount
        if remaining == Decimal('0.00'):
            return 'Paid'
        if self.expected_return_date and self.expected_return_date < datetime.date.today():
            return 'Overdue'
        if remaining == self.amount:
            return 'Pending'
        return 'Partially Paid'

    def save(self, *args, **kwargs):
        if self.expense:
            self.expense.amount = self.amount
            self.expense.date = self.date_lent
            self.expense.title = f"Lent to {self.person_name}"
            self.expense.save()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.expense:
            self.expense.delete()
        super().delete(*args, **kwargs)


class LentRepayment(models.Model):
    lent_money = models.ForeignKey(LentMoney, on_delete=models.CASCADE, related_name='repayments')
    amount_received = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_date = models.DateField(default=datetime.date.today)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f"₹{self.amount_received} received on {self.payment_date}"


