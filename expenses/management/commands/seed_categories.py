from django.core.management.base import BaseCommand
from expenses.models import Category


DEFAULT_CATEGORIES = [
    {'name': 'Food',          'icon': '🍔', 'color': '#FF6B6B'},
    {'name': 'Travel',        'icon': '✈️', 'color': '#45B7D1'},
    {'name': 'Shopping',      'icon': '🛍️', 'color': '#DDA0DD'},
    {'name': 'Bills',         'icon': '📋', 'color': '#F7DC6F'},
    {'name': 'Education',     'icon': '📚', 'color': '#4ECDC4'},
    {'name': 'Entertainment', 'icon': '🎬', 'color': '#96CEB4'},
    {'name': 'Health',        'icon': '🏥', 'color': '#98D8C8'},
    {'name': 'Technology',    'icon': '💻', 'color': '#F0A500'},
    {'name': 'Personal',      'icon': '👤', 'color': '#74B9FF'},
    {'name': 'Other',         'icon': '📦', 'color': '#AEB6BF'},
]


class Command(BaseCommand):
    help = 'Seeds the database with default expense categories'

    def handle(self, *args, **options):
        created_count = 0
        for cat_data in DEFAULT_CATEGORIES:
            obj, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'icon': cat_data['icon'],
                    'color': cat_data['color'],
                    'is_default': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Created: {cat_data["name"]}'))
            else:
                self.stdout.write(f'  Already exists: {cat_data["name"]}')

        self.stdout.write(
            self.style.SUCCESS(f'\nDone. {created_count} new categories created.')
        )
