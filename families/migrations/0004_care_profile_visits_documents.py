from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('families', '0003_checkin_schedule')]
    operations = [
        migrations.CreateModel(name='CareProfile', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('allergies', models.CharField(blank=True, max_length=500)), ('diagnoses', models.CharField(blank=True, max_length=700)),
            ('doctor_name', models.CharField(blank=True, max_length=120)), ('doctor_phone', models.CharField(blank=True, max_length=32)),
            ('health_card_number', models.CharField(blank=True, max_length=80)), ('updated_at', models.DateTimeField(auto_now=True)),
            ('user', models.OneToOneField(on_delete=models.deletion.CASCADE, related_name='care_profile', to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name='FamilyVisit', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('scheduled_for', models.DateTimeField()), ('status', models.CharField(choices=[('planned', 'Planirano'), ('en_route', 'Krećem'), ('arrived', 'Stigao/la sam'), ('completed', 'Završeno')], default='planned', max_length=16)),
            ('note', models.CharField(blank=True, max_length=300)), ('created_at', models.DateTimeField(auto_now_add=True)),
            ('family', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='visits', to='families.family')),
            ('visitor', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='family_visits', to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ['scheduled_for']}),
        migrations.CreateModel(name='CareDocument', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('title', models.CharField(max_length=160)), ('category', models.CharField(choices=[('report', 'Nalaz'), ('discharge', 'Otpusna lista'), ('prescription', 'Recept / terapija'), ('other', 'Drugo')], default='other', max_length=16)),
            ('document', models.FileField(upload_to='care_documents/')), ('created_at', models.DateTimeField(auto_now_add=True)),
            ('uploaded_by', models.ForeignKey(null=True, on_delete=models.deletion.SET_NULL, related_name='uploaded_care_documents', to=settings.AUTH_USER_MODEL)),
            ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='care_documents', to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ['-created_at']}),
    ]
