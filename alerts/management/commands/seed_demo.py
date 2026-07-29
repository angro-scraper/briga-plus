from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from families.models import Family, Membership
from checkins.models import CheckIn
from reminders.models import Reminder
from caretasks.models import CareTask
from messaging.models import Message
from emergencies.models import EmergencyAlert

class Command(BaseCommand):
    help = 'Kreira ili osvežava bezbedne lokalne demo podatke za Briga+.'

    def handle(self, *args, **options):
        accounts = [('demo', 'Administrator'), ('mama', 'Jelena'), ('ana', 'Ana')]
        users = {}
        for username, first_name in accounts:
            user, _ = User.objects.get_or_create(username=username, defaults={'first_name': first_name})
            user.first_name = first_name; user.set_password('BrigaPlus2026!'); user.save(); users[username] = user
        family, _ = Family.objects.get_or_create(name='Porodica Petrović')
        Membership.objects.update_or_create(user=users['demo'], family=family, defaults={'role': Membership.Role.ADMIN})
        Membership.objects.update_or_create(user=users['mama'], family=family, defaults={'role': Membership.Role.SENIOR, 'alert_after_minutes': 180})
        Membership.objects.update_or_create(user=users['ana'], family=family, defaults={'role': Membership.Role.CAREGIVER})
        now = timezone.now()
        CheckIn.objects.get_or_create(user=users['mama'], created_at__date=now.date(), defaults={'note': 'Dobro sam, hvala.'})
        Reminder.objects.get_or_create(user=users['mama'], title='Jutarnja terapija', defaults={'kind': Reminder.Kind.MEDICINE, 'scheduled_for': now.replace(hour=9, minute=0, second=0, microsecond=0), 'repeat_daily': True})
        Reminder.objects.get_or_create(user=users['mama'], title='Kontrola kod kardiologa', defaults={'kind': Reminder.Kind.APPOINTMENT, 'scheduled_for': now + timedelta(days=4)})
        CareTask.objects.get_or_create(family=family, title='Pozvati mamu posle ručka', defaults={'assignee': users['ana'], 'due_at': now + timedelta(hours=3)})
        CareTask.objects.get_or_create(family=family, title='Preuzeti terapiju iz apoteke', defaults={'assignee': users['demo'], 'due_at': now + timedelta(days=1)})
        Message.objects.get_or_create(family=family, sender=users['ana'], body='Dobro jutro, pozvaću mamu posle ručka.')
        self.stdout.write(self.style.SUCCESS('Demo porodica je spremna. Prijava: demo / BrigaPlus2026!'))
