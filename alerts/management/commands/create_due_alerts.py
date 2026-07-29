from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from alerts.models import Alert
from alerts.push import send_push_alert
from families.models import Membership
from checkins.models import CheckIn
from reminders.models import Reminder

class Command(BaseCommand):
    help = 'Kreira interna upozorenja za dospele podsetnike i propuštene potvrde.'

    def handle(self, *args, **options):
        now = timezone.now()
        for reminder in Reminder.objects.filter(completed_at__isnull=True, scheduled_for__lte=now):
            if not Alert.objects.filter(recipient=reminder.user, kind=Alert.Kind.REMINDER, body=str(reminder.pk), created_at__date=now.date()).exists():
                alert = Alert.objects.create(recipient=reminder.user, kind=Alert.Kind.REMINDER, title=f'Vreme je za: {reminder.title}', body=str(reminder.pk))
                send_push_alert(alert)
        for member in Membership.objects.filter(role=Membership.Role.SENIOR).select_related('user', 'family'):
            due_at = timezone.make_aware(datetime.combine(now.date(), member.checkin_due_time))
            latest = CheckIn.objects.filter(user=member.user, created_at__date=now.date()).first()
            if latest or now < due_at:
                continue
            if now >= due_at + timedelta(minutes=member.gentle_reminder_minutes):
                marker = f'nezan-podsetnik-{member.user_id}'
                if not Alert.objects.filter(recipient=member.user, kind=Alert.Kind.CHECKIN, body=marker, created_at__date=now.date()).exists():
                    alert = Alert.objects.create(
                        recipient=member.user, kind=Alert.Kind.CHECKIN, title='Kratko nam javite kako ste',
                        body=marker, url='/',
                    )
                    send_push_alert(alert)
            if now < due_at + timedelta(minutes=member.alert_after_minutes):
                continue
            for carer in member.family.memberships.exclude(user=member.user).values_list('user_id', flat=True):
                marker = f'nema-potvrde-{member.user_id}'
                if not Alert.objects.filter(recipient_id=carer, kind=Alert.Kind.CHECKIN, body=marker, created_at__date=now.date()).exists():
                    alert = Alert.objects.create(recipient_id=carer, kind=Alert.Kind.CHECKIN, title=f'Nema potvrde: {member.user.username}', body=marker, url='/')
                    send_push_alert(alert)
        self.stdout.write(self.style.SUCCESS('Upozorenja su proverena.'))
