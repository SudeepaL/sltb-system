from django import forms
from .models import Bus, Conductor, Driver

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
            'current_fuel_liters',
            'fuel_efficiency_km_per_liter',
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