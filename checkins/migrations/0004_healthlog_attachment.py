from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('checkins', '0003_mood_entry')]

    operations = [
        migrations.AddField(
            model_name='healthlog',
            name='attachment',
            field=models.FileField(blank=True, upload_to='health_logs/'),
        ),
    ]
