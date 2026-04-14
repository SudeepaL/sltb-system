from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from .forms import BusForm
from .models import Bus, Trip

MODULE_BUTTONS = [
    'Buses',
    'Drivers',
    'Conductors',
    'Scheduling',
    'Fuel Usage',
    'Maintenance',
    'Current Trips',
    'View Timetable',
]

# Create your views here.
def _get_bus_trip_rows():
    rows = []
    buses = Bus.objects.order_by('bus_code')

    for bus in buses:
        current_trip = (
            Trip.objects.select_related(
                'schedule__driver',
                'schedule__conductor',
                'schedule__timetable__route',
            )
            .filter(schedule__bus=bus)
            .exclude(t_status='COMPLETED')
            .order_by('-actual_departure_time', '-id')
            .first()
        )

        if not current_trip:
            current_trip = (
                Trip.objects.select_related(
                    'schedule__driver',
                    'schedule__conductor',
                    'schedule__timetable__route',
                )
                .filter(schedule__bus=bus)
                .order_by('-actual_departure_time', '-id')
                .first()
            )

        schedule_label = '-'
        driver_name = '-'
        conductor_name = '-'

        if current_trip:
            route = current_trip.schedule.timetable.route
            schedule_label = f'{route.start_location}-{route.end_location}'
            if current_trip.schedule.driver:
                driver_name = current_trip.schedule.driver.driver_name
            if current_trip.schedule.conductor:
                conductor_name = current_trip.schedule.conductor.conductor_name

        rows.append(
            {
                'bus': bus,
                'current_route': schedule_label,
                'driver_name': driver_name,
                'conductor_name': conductor_name,
            }
        )

    return rows


def bus_dashboard(request):
    selected_bus_id = request.GET.get('bus')
    bus_rows = _get_bus_trip_rows()

    selected_bus = bus_rows[0]['bus'] if bus_rows else None
    if selected_bus_id:
        selected_bus = get_object_or_404(Bus, id=selected_bus_id)

    on_route_count = Bus.objects.filter(status='ON_ROUTE').count()
    maintenance_count = Bus.objects.filter(status='MAINTENANCE').count()

    context = {
        'bus_rows': bus_rows,
        'selected_bus': selected_bus,
        'total_buses': Bus.objects.count(),
        'available_buses': Bus.objects.filter(status='AVAILABLE').count(),
        'on_route_buses': on_route_count,
        'maintenance_buses': maintenance_count,
        'module_buttons': MODULE_BUTTONS,
    }

    return render(request, 'core/bus_dashboard.html', context)


def manage_bus(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)

    if request.method == 'POST':
        if 'delete_bus' in request.POST:
            bus.delete()
            return redirect('bus_dashboard')

        form = BusForm(request.POST, request.FILES, instance=bus)
        if form.is_valid():
            form.save()
            return redirect(f"{reverse('bus_dashboard')}?bus={bus.id}")
    else:
        form = BusForm(instance=bus)

    return render(
        request,
        'core/manage_bus.html',
        {'form': form, 'bus': bus, 'module_buttons': MODULE_BUTTONS},
    )


def add_bus(request):
    if request.method == 'POST':
        form = BusForm(request.POST, request.FILES)
        if form.is_valid():
            created_bus = form.save()
            return redirect(f"{reverse('bus_dashboard')}?bus={created_bus.id}")
    else:
        form = BusForm()

    return render(
        request,
        'core/add_bus.html',
        {'form': form, 'module_buttons': MODULE_BUTTONS},
    )