from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_trip_delay_started_at_alter_schedule_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='DepotFuelTank',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_level_liters', models.FloatField(default=15000)),
                ('max_capacity_liters', models.FloatField(default=30000)),
                ('last_refill_date', models.DateField(null=True, blank=True)),
                ('next_refill_date', models.DateField(null=True, blank=True)),
                ('last_refill_amount', models.FloatField(null=True, blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
