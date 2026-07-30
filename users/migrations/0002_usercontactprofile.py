from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_privacyconsent_auditevent'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserContactProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(max_length=32, verbose_name='broj telefona')),
                ('address', models.CharField(max_length=240, verbose_name='adresa')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=models.deletion.CASCADE, related_name='contact_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
