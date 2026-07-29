from django.contrib import admin
from .models import Reminder
@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'kind', 'dosage', 'scheduled_for', 'completed_at')
    list_filter = ('kind', 'repeat_daily', 'completed_at')

# Register your models here.
