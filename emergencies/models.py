from django.conf import settings
from django.db import models
from families.models import Family

class EmergencyAlert(models.Model):
    class Kind(models.TextChoices):
        SOS = 'sos', 'SOS — hitno'
        CALL = 'call', 'Treba mi poziv'
        UNWELL = 'unwell', 'Ne osećam se dobro'
        HELP = 'help', 'Treba mi pomoć'
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='emergencies')
    raised_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    accuracy_meters = models.PositiveIntegerField(null=True, blank=True)
    note = models.CharField(max_length=280, blank=True)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.SOS)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='acknowledged_emergencies')
    responder_en_route_at = models.DateTimeField(null=True, blank=True)
    responder = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='en_route_emergencies')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']
