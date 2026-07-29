from django.conf import settings
from django.db import models

class CheckIn(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='checkins')
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=240, blank=True)
    class Meta: ordering = ['-created_at']
