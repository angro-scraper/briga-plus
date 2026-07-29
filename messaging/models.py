from django.conf import settings
from django.db import models
from families.models import Family

class Message(models.Model):
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['created_at']
