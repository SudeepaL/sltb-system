from django.contrib import admin
from .models import Bus, Driver, Conductor, Route, Stop, RouteStop, Schedule


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('bus_code', 'bus_number', 'status')
    #search_fields = ('bus_number',)
    #list_filter = ('status',)

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('driver_name','driving_license_number','phone_number','email','driver_status')
    #search_fields =  ('name', 'license_number')
    #list_filter = ('driver_status',)

@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    list_display = ('conductor_name','c_phone_number','c_email','conductor_status')

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('route_number', 'start_location', 'end_location')


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ('stop_name', 'latitude', 'longitude')

@admin.register(RouteStop)
class RouteStopAdmin(admin.ModelAdmin):
    list_display = ('route', 'stop', 'order')

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('route', 'bus', 'driver', 'date', 'depature_time')


# Register your models here.
