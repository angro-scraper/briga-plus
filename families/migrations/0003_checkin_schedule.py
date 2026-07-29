import datetime
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('families', '0002_emergencycontact')]
    operations = [
        migrations.AddField(model_name='membership', name='checkin_due_time', field=models.TimeField(default=datetime.time(10, 0))),
        migrations.AddField(model_name='membership', name='gentle_reminder_minutes', field=models.PositiveIntegerField(default=30)),
    ]
