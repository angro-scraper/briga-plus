from django.conf import settings
from django.db import models


class PrivacyConsent(models.Model):
    """Dokaz da je korisnik prihvatio aktuelnu politiku privatnosti."""

    POLICY_VERSION = '2026-07-30'
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='privacy_consent')
    policy_version = models.CharField(max_length=32, default=POLICY_VERSION)
    accepted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Privatnost: {self.user}'


class AuditEvent(models.Model):
    """Neizmenjiv, kratak trag radnji koje utiču na bezbednost i pristup."""

    class Event(models.TextChoices):
        CONSENT = 'consent', 'Prihvaćena politika privatnosti'
        INVITE_CREATED = 'invite_created', 'Napravljena pozivnica'
        ACCESS_CHANGED = 'access_changed', 'Promenjen nivo pristupa'
        SOS_CREATED = 'sos_created', 'Poslat SOS'
        SOS_UPDATED = 'sos_updated', 'Promenjen status SOS-a'
        ACCOUNT_DELETED = 'account_deleted', 'Obrisan nalog'
        PLATFORM_EMERGENCY = 'platform_emergency', 'Platformska intervencija'

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_events')
    family_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    event = models.CharField(max_length=32, choices=Event.choices)
    target = models.CharField(max_length=160, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_event_display()} · {self.created_at:%d.%m.%Y %H:%M}'

# Create your models here.
