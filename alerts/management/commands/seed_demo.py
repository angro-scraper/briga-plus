from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from families.models import EmergencyContact, Family, Membership
from checkins.models import CheckIn
from reminders.models import Reminder
from caretasks.models import CareTask
from messaging.models import Message
from emergencies.models import EmergencyAlert

class Command(BaseCommand):
    help = 'Kreira ili osvežava bezbedne lokalne demo podatke za Briga+.'

    @staticmethod
    def ensure_reminder(user, title, defaults):
        """Sačuvaj postojeći aktivni demo podsetnik bez oslanjanja na nejedinstven naslov."""
        reminder = Reminder.objects.filter(
            user=user,
            title=title,
            completed_at__isnull=True,
        ).order_by('id').first()
        if reminder:
            return reminder
        return Reminder.objects.create(user=user, title=title, **defaults)

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
        self.ensure_reminder(users['mama'], 'Jutarnja terapija', {'kind': Reminder.Kind.MEDICINE, 'scheduled_for': now.replace(hour=9, minute=0, second=0, microsecond=0), 'repeat_daily': True, 'dosage': '1 tableta od 5 mg', 'instructions': 'Posle doručka'})
        self.ensure_reminder(users['mama'], 'Kontrola kod kardiologa', {'kind': Reminder.Kind.APPOINTMENT, 'scheduled_for': now + timedelta(days=4)})
        CareTask.objects.get_or_create(family=family, title='Pozvati mamu posle ručka', defaults={'assignee': users['ana'], 'due_at': now + timedelta(hours=3)})
        CareTask.objects.get_or_create(family=family, title='Preuzeti terapiju iz apoteke', defaults={'assignee': users['demo'], 'due_at': now + timedelta(days=1)})
        EmergencyContact.objects.get_or_create(family=family, name='Ana Petrović', defaults={'relationship': 'Ćerka', 'phone': '+381641234567', 'priority': 1})
        Message.objects.get_or_create(family=family, sender=users['ana'], body='Dobro jutro, pozvaću mamu posle ručka.')
        self.stdout.write(self.style.SUCCESS('Demo porodica je spremna. Prijava: demo / BrigaPlus2026!'))
