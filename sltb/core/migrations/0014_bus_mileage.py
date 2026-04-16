from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_remove_bus_milage'),
    ]

    operations = [
        migrations.AddField(
            model_name='bus',
            name='mileage',
            field=models.PositiveIntegerField(default=0, help_text='Current mileage of the bus in km'),
        ),
    ]
