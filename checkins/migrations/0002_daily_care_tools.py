from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('checkins', '0001_initial')]

    operations = [
        migrations.AddField(model_name='checkin', name='period', field=models.CharField(choices=[('any', 'Potvrda'), ('morning', 'Jutro'), ('evening', 'Veče')], default='any', max_length=12)),
        migrations.CreateModel(name='DailyRoutine', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('title', models.CharField(max_length=140)),
            ('category', models.CharField(choices=[('medicine', 'Lekovi'), ('wellbeing', 'Dobro stanje'), ('movement', 'Kretanje'), ('contact', 'Kontakt'), ('other', 'Drugo')], default='wellbeing', max_length=16)),
            ('part_of_day', models.CharField(choices=[('morning', 'Jutro'), ('day', 'Tokom dana'), ('evening', 'Veče')], default='day', max_length=16)),
            ('active', models.BooleanField(default=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='daily_routines', to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ['part_of_day', 'title']}),
        migrations.CreateModel(name='HealthLog', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('kind', models.CharField(choices=[('pressure', 'Krvni pritisak'), ('glucose', 'Šećer u krvi'), ('symptom', 'Simptom / kako se osećam'), ('note', 'Napomena')], max_length=16)),
            ('value', models.CharField(blank=True, max_length=80)),
            ('note', models.CharField(blank=True, max_length=300)),
            ('recorded_at', models.DateTimeField()),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='health_logs', to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ['-recorded_at']}),
        migrations.CreateModel(name='RoutineCompletion', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('completed_on', models.DateField()),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('routine', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='completions', to='checkins.dailyroutine')),
            ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='routine_completions', to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddConstraint(model_name='routinecompletion', constraint=models.UniqueConstraint(fields=('routine', 'completed_on'), name='one_routine_completion_per_day')),
    ]
