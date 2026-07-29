import uuid

import django.db.models.deletion
import families.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('families', '0005_care_device'),
    ]

    operations = [
        migrations.AddField(
            model_name='membership',
            name='access_level',
            field=models.CharField(choices=[('basic', 'Osnovni pristup'), ('health', 'Zdravstveni pristup'), ('full', 'Pun porodični pristup')], default='full', max_length=16),
        ),
        migrations.CreateModel(
            name='FamilyInvite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient_label', models.CharField(blank=True, max_length=120)),
                ('role', models.CharField(choices=[('admin', 'Administrator porodice'), ('caregiver', 'Član porodice'), ('senior', 'Osoba o kojoj se brine')], max_length=16)),
                ('access_level', models.CharField(choices=[('basic', 'Osnovni pristup'), ('health', 'Zdravstveni pristup'), ('full', 'Pun porodični pristup')], default='basic', max_length=16)),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('expires_at', models.DateTimeField(default=families.models.default_invite_expiry)),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('accepted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='accepted_family_invites', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_family_invites', to=settings.AUTH_USER_MODEL)),
                ('family', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invites', to='families.family')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
