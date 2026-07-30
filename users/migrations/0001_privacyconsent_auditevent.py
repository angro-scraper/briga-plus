# Generated manually for Briga+ production readiness.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PrivacyConsent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('policy_version', models.CharField(default='2026-07-30', max_length=32)),
                ('accepted_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='privacy_consent', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='AuditEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('family_id', models.PositiveBigIntegerField(blank=True, db_index=True, null=True)),
                ('event', models.CharField(choices=[('consent', 'Prihvaćena politika privatnosti'), ('invite_created', 'Napravljena pozivnica'), ('access_changed', 'Promenjen nivo pristupa'), ('sos_created', 'Poslat SOS'), ('sos_updated', 'Promenjen status SOS-a'), ('account_deleted', 'Obrisan nalog'), ('platform_emergency', 'Platformska intervencija')], max_length=32)),
                ('target', models.CharField(blank=True, max_length=160)),
                ('detail', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_events', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
