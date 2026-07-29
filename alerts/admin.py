from django.contrib import admin
from .models import Alert, PushSubscription
admin.site.register([Alert, PushSubscription])
