import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_alter_driver_driver_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schedule',
            name='bus',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.bus'),
        ),
    ]