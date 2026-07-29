from django.conf import settings
from django.db import models

class Family(models.Model):
    name = models.CharField('naziv porodice', max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name

class Membership(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrator porodice'
        CAREGIVER = 'caregiver', 'Član porodice'
        SENIOR = 'senior', 'Osoba o kojoj se brine'
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='family_memberships')
    role = models.CharField(max_length=16, choices=Role.choices)
    alert_after_minutes = models.PositiveIntegerField(default=120)
    class Meta: unique_together = ('family', 'user')
    def __str__(self): return f'{self.user} — {self.family}'
