from django.contrib import admin
from .models import CareDevice, CareDocument, CareProfile, EmergencyContact, Family, FamilyInvite, FamilyVisit, Membership
admin.site.register([Family, Membership, FamilyInvite, EmergencyContact, CareProfile, FamilyVisit, CareDocument, CareDevice])

# Register your models here.
