from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('caretasks', '0001_initial')]
    operations = [
        migrations.AddField(model_name='caretask', name='category', field=models.CharField(default='other', max_length=16)),
        migrations.AddField(model_name='caretask', name='notes', field=models.CharField(blank=True, max_length=300)),
    ]
