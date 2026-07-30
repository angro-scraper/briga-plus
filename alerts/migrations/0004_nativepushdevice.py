from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('alerts', '0003_alter_alert_kind')]

    operations = [
        migrations.CreateModel(
            name='NativePushDevice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('platform', models.CharField(choices=[('android', 'Android'), ('ios', 'iPhone / iPad')], max_length=12)),
                ('token', models.CharField(max_length=512, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='native_push_devices', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
