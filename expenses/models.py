from django.db import models
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

    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=10, default='📦')
    color = models.CharField(max_length=7, default='#AEB6BF')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

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
        default='cash'
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.title} — ₹{self.amount}"


class Budget(models.Model):
    """Monthly budget. One record per month."""
    month = models.DateField(unique=True)  # stored as first day of the month
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1.00'))]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-month']

    def __str__(self):
        return f"Budget for {self.month.strftime('%B %Y')}: ₹{self.amount}"


class CashBalance(models.Model):
    """Single-row table to track current cash balance."""
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
        return f"Cash Balance: ₹{self.balance}"

    def save(self, *args, **kwargs):
        # enforce single-row pattern
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_balance(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'balance': Decimal('0.00')})
        return obj
