from django.contrib import admin
from .models import Bus, Driver


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('bus_code', 'bus_number', 'status')


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = (
        'driver_name',
        'driving_license_number',
        'phone_number',
        'email',
        'driver_status'
    )

# Register your models here.
