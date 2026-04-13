from django import forms
from .models import Bus

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