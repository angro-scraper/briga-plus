from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('emergencies', '0001_initial')]
    operations = [
        migrations.AddField(model_name='emergencyalert', name='kind', field=models.CharField(choices=[('sos', 'SOS — hitno'), ('call', 'Treba mi poziv'), ('unwell', 'Ne osećam se dobro'), ('help', 'Treba mi pomoć')], default='sos', max_length=12)),
        migrations.AddField(model_name='emergencyalert', name='acknowledged_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='emergencyalert', name='acknowledged_by', field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='acknowledged_emergencies', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='emergencyalert', name='responder_en_route_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='emergencyalert', name='responder', field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='en_route_emergencies', to=settings.AUTH_USER_MODEL)),
    ]
