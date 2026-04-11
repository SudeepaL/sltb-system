from django.contrib import admin
from django.contrib import messages 
from .models import Bus, Driver, Conductor, Route, Stop, RouteStop, Schedule, TimeTable, Trip, StaffAttendance, FuelTransaction, BusMaintenance

@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('bus_code', 'bus_number', 'status', 'current_fuel_liters', 'fuel_efficiency_km_per_liter')
    search_fields = ('bus_code', 'bus_number')

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('driver_name','driving_license_number','phone_number','email','driver_status')
    #search_fields =  ('name', 'license_number')
    #list_filter = ('driver_status',)

@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    list_display = ('conductor_name','c_phone_number','c_email','conductor_status')
    actions = ['auto_assign_staff_rule_based']

    @admin.action(description='Auto assign available drivers and conductors (rule-based)')
    def auto_assign_staff_rule_based(self, request, queryset):
        assigned_count = Schedule.auto_assign_staff_rule_based(schedule_ids=list(queryset.values_list('id', flat=True)))
        self.message_user(
            request,
            f"Assigned staff for {assigned_count} schedule(s).",
            level=messages.SUCCESS if assigned_count else messages.WARNING,
        )

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
    list_display = ('timetable', 'bus', 'driver', 'conductor', 'date', 'status')

@admin.register(TimeTable)
class TimeTableAdmin(admin.ModelAdmin):
    list_display = ('route', 'departure_time', 'direction', 'day_of_week')

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('schedule', 't_status', 'actual_departure_time')

@admin.register(FuelTransaction)
class FuelTransactionAdmin(admin.ModelAdmin):
    list_display = ('bus', 'transaction_type', 'amount_liters', 'created_at')
    list_filter = ('transaction_type',)
    search_fields = ('bus__bus_code',)

@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = ('staff_type', 'staff_name', 'status', 'clock_in_time', 'clock_out_time', 'updated_at')
    readonly_fields = ('clock_in_time', 'clock_out_time', 'updated_at')

@admin.register(BusMaintenance)
class BusMaintenanceAdmin(admin.ModelAdmin):
    list_display = ('bus', 'service_date', 'mileage', 'next_service_due_mileage', 'created_at')
    list_filter = ('service_date', 'bus')
    search_fields = ('bus__bus_code', 'bus__bus_number', 'service_history', 'maintenance_details')

# Register your models here.
