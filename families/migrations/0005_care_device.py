from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('families', '0004_care_profile_visits_documents')]
    operations = [
        migrations.CreateModel(name='CareDevice', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('name', models.CharField(default='Briga+ uređaj', max_length=80)), ('serial_number', models.CharField(blank=True, max_length=80)),
            ('device_type', models.CharField(choices=[('bracelet', 'SOS narukvica'), ('watch', 'Pametni sat'), ('other', 'Drugi uređaj')], default='bracelet', max_length=16)),
            ('status', models.CharField(choices=[('ready', 'Spreman za povezivanje'), ('connected', 'Povezan'), ('offline', 'Nije dostupan')], default='ready', max_length=16)),
            ('battery_percent', models.PositiveSmallIntegerField(blank=True, null=True)), ('last_seen_at', models.DateTimeField(blank=True, null=True)), ('created_at', models.DateTimeField(auto_now_add=True)),
            ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='care_devices', to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ['-created_at']}),
    ]
