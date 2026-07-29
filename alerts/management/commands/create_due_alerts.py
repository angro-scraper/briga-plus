from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from alerts.models import Alert
from families.models import Membership
from checkins.models import CheckIn
from reminders.models import Reminder

class Command(BaseCommand):
    help = 'Kreira interna upozorenja za dospele podsetnike i propuštene potvrde.'

    def handle(self, *args, **options):
        now = timezone.now()
        for reminder in Reminder.objects.filter(completed_at__isnull=True, scheduled_for__lte=now):
            if not Alert.objects.filter(recipient=reminder.user, kind=Alert.Kind.REMINDER, body=str(reminder.pk), created_at__date=now.date()).exists():
                Alert.objects.create(recipient=reminder.user, kind=Alert.Kind.REMINDER, title=f'Vreme je za: {reminder.title}', body=str(reminder.pk))
        for member in Membership.objects.filter(role=Membership.Role.SENIOR).select_related('user', 'family'):
            latest = CheckIn.objects.filter(user=member.user).first()
            if latest and latest.created_at >= now - timedelta(minutes=member.alert_after_minutes):
                continue
            for carer in member.family.memberships.exclude(user=member.user).values_list('user_id', flat=True):
                if not Alert.objects.filter(recipient_id=carer, kind=Alert.Kind.CHECKIN, body=str(member.user_id), created_at__date=now.date()).exists():
                    Alert.objects.create(recipient_id=carer, kind=Alert.Kind.CHECKIN, title=f'Nema potvrde: {member.user.username}', body=str(member.user_id))
        self.stdout.write(self.style.SUCCESS('Upozorenja su proverena.'))
