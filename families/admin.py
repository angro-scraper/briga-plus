from django.contrib import admin
from .models import EmergencyContact, Family, Membership
admin.site.register([Family, Membership, EmergencyContact])

# Register your models here.
