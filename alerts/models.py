from django.conf import settings
from django.db import models

class Alert(models.Model):
    class Kind(models.TextChoices):
        SOS = 'sos', 'SOS'
        CHECKIN = 'checkin', 'Propuštena potvrda'
        REMINDER = 'reminder', 'Podsetnik'
        MESSAGE = 'message', 'Poruka'
        NEED_HELP = 'need_help', 'Potreban je poziv / pomoć'
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='alerts')
    kind = models.CharField(max_length=16, choices=Kind.choices)
    title = models.CharField(max_length=160)
    body = models.CharField(max_length=500, blank=True)
    url = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    class Meta: ordering = ['-created_at']


class PushSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.URLField(unique=True, max_length=500)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
