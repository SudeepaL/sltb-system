from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_bus_mileage'),
    ]

    operations = [
        migrations.AddField(
            model_name='busmaintenance',
            name='estimated_maintenance_duration',
            field=models.DateTimeField(blank=True, help_text='Estimated date and time maintenance will be completed', null=True),
        ),
        migrations.AddField(
            model_name='busmaintenance',
            name='estimated_cost',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Estimated cost in LKR', max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='busmaintenance',
            name='maintenance_status',
            field=models.CharField(choices=[('IN_SERVICE', 'In Service'), ('COMPLETED', 'Completed')], default='IN_SERVICE', max_length=20),
        ),
        migrations.AddField(
            model_name='busmaintenance',
            name='actual_completion_date',
            field=models.DateTimeField(blank=True, help_text='Actual date and time maintenance was completed', null=True),
        ),
        migrations.AddField(
            model_name='busmaintenance',
            name='actual_cost',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Actual cost in LKR', max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='busmaintenance',
            name='service_bill',
            field=models.FileField(blank=True, help_text='Upload bill or photo of the bill', null=True, upload_to='service_bills/'),
        ),
    ]
