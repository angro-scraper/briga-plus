from django.conf import settings
from django.db import models
from families.models import Family

class CareTask(models.Model):
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=180)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_tasks')
    due_at = models.DateTimeField(null=True, blank=True)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['done', 'due_at']
