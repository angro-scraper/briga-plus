from django.conf import settings
from django.db import models

class Reminder(models.Model):
    class Kind(models.TextChoices): MEDICINE='medicine','Lek'; APPOINTMENT='appointment','Pregled'; OTHER='other','Drugo'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reminders')
    title = models.CharField(max_length=160)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.MEDICINE)
    scheduled_for = models.DateTimeField()
    repeat_daily = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    class Meta: ordering = ['scheduled_for']
