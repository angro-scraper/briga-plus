from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('checkins', '0002_daily_care_tools')]
    operations = [
        migrations.CreateModel(name='MoodEntry', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('mood', models.CharField(choices=[('good', 'Dobro'), ('tired', 'Umorno'), ('low', 'Loše')], max_length=12)),
            ('note', models.CharField(blank=True, max_length=240)), ('recorded_on', models.DateField()), ('created_at', models.DateTimeField(auto_now_add=True)),
            ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='mood_entries', to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ['-recorded_on']}),
        migrations.AddConstraint(model_name='moodentry', constraint=models.UniqueConstraint(fields=('user', 'recorded_on'), name='one_mood_per_day')),
    ]
