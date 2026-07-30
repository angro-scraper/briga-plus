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


class UserContactProfile(models.Model):
    """Kontakt podaci naloga; ne prikazuju se javno niti drugim porodicama."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contact_profile')
    phone = models.CharField('broj telefona', max_length=32)
    address = models.CharField('adresa', max_length=240)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Kontakt: {self.user}'


class PilotFeedback(models.Model):
    """Kratka povratna informacija pilota, vidljiva samo platformskom timu."""

    class Category(models.TextChoices):
        EASE = 'ease', 'Lakše korišćenje'
        NOTIFICATION = 'notification', 'Obaveštenja'
        SOS = 'sos', 'SOS i bezbednost'
        ISSUE = 'issue', 'Problem u radu'
        IDEA = 'idea', 'Predlog'

    class Rating(models.TextChoices):
        GOOD = 'good', 'Dobro radi'
        OK = 'ok', 'Može bolje'
        BAD = 'bad', 'Ne radi kako treba'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pilot_feedback')
    family = models.ForeignKey('families.Family', null=True, blank=True, on_delete=models.SET_NULL, related_name='pilot_feedback')
    category = models.CharField(max_length=16, choices=Category.choices)
    rating = models.CharField(max_length=8, choices=Rating.choices)
    message = models.CharField(max_length=800)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_category_display()} · {self.user}'


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
