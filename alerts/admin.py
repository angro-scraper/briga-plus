from django.contrib import admin
from .models import Alert, NativePushDevice, PushSubscription
admin.site.register([Alert, PushSubscription, NativePushDevice])
