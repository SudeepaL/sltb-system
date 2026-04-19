from django import forms
from .models import Bus, BusMaintenance, Conductor, Driver, Route, Schedule, Stop, TimeTable


class BusForm(forms.ModelForm):
    class Meta:
        model = Bus
        fields = [
            'bus_number',
            'bus_code',
            'model',
            'capacity',
            'bus_type',
            'status',
            'depot',
            'fuel_capacity_liters',
            'current_fuel_liters',
            'fuel_efficiency_km_per_liter',
            'mileage',
            'image',
        ]


class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = [
            'driver_name',
            'dob',
            'nic_number',
            'driving_license_number',
            'gender',
            'phone_number',
            'email',
            'driver_address',
            'driver_status',
            'driver_registration_date',
            'driver_id_image',
        ]
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'driver_registration_date': forms.DateInput(attrs={'type': 'date'}),
        }

class ConductorForm(forms.ModelForm):
    class Meta:
        model = Conductor
        fields = [
            'conductor_name',
            'c_dob',
            'c_nic_number',
            'c_gender',
            'c_phone_number',
            'c_email',
            'conductor_address',
            'conductor_status',
            'conductor_registration_date',
            'conductor_id_image',
        
        ]
        widgets = {
            'c_dob': forms.DateInput(attrs={'type': 'date'}),
            'conductor_registration_date': forms.DateInput(attrs={'type': 'date'}),
        }


class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = [
            'route_number',
            'start_location',
            'end_location',
            'distance',
            'estimated_duration',
        ]    

class StopForm(forms.ModelForm):
    class Meta:
        model = Stop
        fields = [
            'stop_name',
            'latitude',
            'longitude',
        ]   

class TimeTableForm(forms.ModelForm):
    class Meta:
        model = TimeTable
        fields = [
            'route',
            'departure_time',
            'arrival_time',
            'day_of_week',
            'direction',
        ]

class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = [
            'timetable',
            'bus',
            'driver',
            'conductor',
            'date',
            'status',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }


class BusMaintenanceForm(forms.ModelForm):
    class Meta:
        model = BusMaintenance
        fields = [
            'bus',
            'service_date',
            'mileage',
            'service_history',
            'maintenance_details',
            'next_service_due_mileage',
        ]
        widgets = {
            'service_date': forms.DateInput(attrs={'type': 'date'}),
        }
