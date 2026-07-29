from django.contrib import admin
from .models import Message, VoiceMessage
admin.site.register([Message, VoiceMessage])

# Register your models here.
