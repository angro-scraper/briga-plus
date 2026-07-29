from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('alerts', '0002_pushsubscription')]
    operations = [
        migrations.AlterField(
            model_name='alert', name='kind',
            field=models.CharField(choices=[('sos', 'SOS'), ('checkin', 'Propuštena potvrda'), ('reminder', 'Podsetnik'), ('message', 'Poruka'), ('need_help', 'Potreban je poziv / pomoć')], max_length=16),
        ),
    ]
