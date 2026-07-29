import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Pravi prvi vlasnički Briga+ nalog iz bezbednih produkcionih promenljivih.'

    def handle(self, *args, **options):
        username = os.environ.get('BRIGA_OWNER_USERNAME', '').strip()
        password = os.environ.get('BRIGA_OWNER_PASSWORD', '')
        email = os.environ.get('BRIGA_OWNER_EMAIL', '').strip()
        if not username or not password:
            self.stdout.write('Owner account is not configured; skipping safely.')
            return

        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_password(password)
        user.email = email or user.email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()
        if created:
            self.stdout.write(self.style.SUCCESS(f'Briga+ owner account created: {username}'))
        else:
            self.stdout.write(f'Briga+ owner account already exists: {username}')
