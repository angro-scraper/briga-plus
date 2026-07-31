from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('emergencies', '0002_response_flow'),
    ]

    operations = [
        migrations.AddField(
            model_name='emergencyalert',
            name='accuracy_meters',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
