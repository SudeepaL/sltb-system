from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_depotfueltank'),
    ]

    operations = [
        migrations.CreateModel(
            name='BusRefuelLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount_liters', models.FloatField()),
                ('fuel_before', models.FloatField()),
                ('fuel_after', models.FloatField()),
                ('depot_level_before', models.FloatField()),
                ('depot_level_after', models.FloatField()),
                ('refueled_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('bus', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='refuel_logs', to='core.bus')),
            ],
            options={
                'ordering': ['-refueled_at'],
            },
        ),
    ]
