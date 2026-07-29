import datetime
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


def default_invite_expiry():
    return timezone.now() + datetime.timedelta(days=7)

class Family(models.Model):
    name = models.CharField('naziv porodice', max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name

class Membership(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrator porodice'
        CAREGIVER = 'caregiver', 'Član porodice'
        SENIOR = 'senior', 'Osoba o kojoj se brine'

    class AccessLevel(models.TextChoices):
        BASIC = 'basic', 'Osnovni pristup'
        HEALTH = 'health', 'Zdravstveni pristup'
        FULL = 'full', 'Pun porodični pristup'
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='family_memberships')
    role = models.CharField(max_length=16, choices=Role.choices)
    access_level = models.CharField(max_length=16, choices=AccessLevel.choices, default=AccessLevel.FULL)
    alert_after_minutes = models.PositiveIntegerField(default=120)
    checkin_due_time = models.TimeField(default=datetime.time(10, 0))
    gentle_reminder_minutes = models.PositiveIntegerField(default=30)
    class Meta: unique_together = ('family', 'user')
    def __str__(self): return f'{self.user} — {self.family}'


class FamilyInvite(models.Model):
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='invites')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_family_invites')
    recipient_label = models.CharField(max_length=120, blank=True)
    role = models.CharField(max_length=16, choices=Membership.Role.choices)
    access_level = models.CharField(max_length=16, choices=Membership.AccessLevel.choices, default=Membership.AccessLevel.BASIC)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    expires_at = models.DateTimeField(default=default_invite_expiry)
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='accepted_family_invites')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def available(self):
        return self.accepted_at is None and self.expires_at > timezone.now()

    def get_absolute_url(self):
        return reverse('poziv', kwargs={'token': self.token})


class EmergencyContact(models.Model):
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='emergency_contacts')
    name = models.CharField(max_length=120)
    relationship = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=32)
    priority = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['priority', 'name']

    def __str__(self): return f'{self.name} ({self.phone})'


class CareProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='care_profile')
    allergies = models.CharField(max_length=500, blank=True)
    diagnoses = models.CharField(max_length=700, blank=True)
    doctor_name = models.CharField(max_length=120, blank=True)
    doctor_phone = models.CharField(max_length=32, blank=True)
    health_card_number = models.CharField(max_length=80, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class FamilyVisit(models.Model):
    class Status(models.TextChoices):
        PLANNED = 'planned', 'Planirano'
        EN_ROUTE = 'en_route', 'Krećem'
        ARRIVED = 'arrived', 'Stigao/la sam'
        COMPLETED = 'completed', 'Završeno'
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='visits')
    visitor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='family_visits')
    scheduled_for = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLANNED)
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheduled_for']


class CareDocument(models.Model):
    class Category(models.TextChoices):
        REPORT = 'report', 'Nalaz'
        DISCHARGE = 'discharge', 'Otpusna lista'
        PRESCRIPTION = 'prescription', 'Recept / terapija'
        OTHER = 'other', 'Drugo'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='care_documents')
    title = models.CharField(max_length=160)
    category = models.CharField(max_length=16, choices=Category.choices, default=Category.OTHER)
    document = models.FileField(upload_to='care_documents/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='uploaded_care_documents')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class CareDevice(models.Model):
    class DeviceType(models.TextChoices):
        BRACELET = 'bracelet', 'SOS narukvica'
        WATCH = 'watch', 'Pametni sat'
        OTHER = 'other', 'Drugi uređaj'
    class Status(models.TextChoices):
        READY = 'ready', 'Spreman za povezivanje'
        CONNECTED = 'connected', 'Povezan'
        OFFLINE = 'offline', 'Nije dostupan'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='care_devices')
    name = models.CharField(max_length=80, default='Briga+ uređaj')
    serial_number = models.CharField(max_length=80, blank=True)
    device_type = models.CharField(max_length=16, choices=DeviceType.choices, default=DeviceType.BRACELET)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.READY)
    battery_percent = models.PositiveSmallIntegerField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
