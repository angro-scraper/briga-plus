from django.contrib import admin

from .models import AuditEvent, PilotFeedback, PrivacyConsent, UserContactProfile


@admin.register(PrivacyConsent)
class PrivacyConsentAdmin(admin.ModelAdmin):
    list_display = ('user', 'policy_version', 'accepted_at')
    search_fields = ('user__username',)
    readonly_fields = ('accepted_at', 'updated_at')


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'event', 'actor', 'family_id', 'target')
    list_filter = ('event',)
    search_fields = ('target', 'actor__username')
    readonly_fields = ('created_at',)


@admin.register(UserContactProfile)
class UserContactProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'updated_at')
    search_fields = ('user__username', 'user__email', 'phone', 'address')
    readonly_fields = ('updated_at',)


@admin.register(PilotFeedback)
class PilotFeedbackAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'family', 'category', 'rating', 'resolved_at')
    list_filter = ('category', 'rating', 'resolved_at')
    search_fields = ('user__username', 'message')
    readonly_fields = ('created_at',)

# Register your models here.
