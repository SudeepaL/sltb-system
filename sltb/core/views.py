from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from .forms import BusForm, BusMaintenanceForm, ConductorForm, DriverForm, RouteForm, ScheduleForm, StopForm, TimeTableForm
from .models import Bus, BusMaintenance, Conductor, Driver, Route, Schedule, RouteStop, Stop, TimeTable, Trip

def _module_buttons(active_module):
    items = [
        {'label': 'Buses', 'url': reverse('bus_dashboard'), 'key': 'buses'},
        {'label': 'Drivers', 'url': reverse('driver_dashboard'), 'key': 'drivers'},
        {'label': 'Conductors', 'url': reverse('conductor_dashboard'), 'key': 'conductors'},
        {'label': 'Manage Routes', 'url': reverse('route_dashboard'), 'key': 'manage_routes'},
        {'label': 'View Timetable', 'url': reverse('timetable_dashboard'), 'key': 'view_timetable'},
         {'label': 'Scheduling', 'url': reverse('scheduling_dashboard'), 'key': 'scheduling'},
        {'label': 'Fuel Usage', 'url': '#', 'key': 'fuel_usage'},
        {'label': 'Maintenance', 'url': reverse('maintenance_dashboard'), 'key': 'maintenance'},
        {'label': 'Current Trips', 'url': '#', 'key': 'current_trips'},
        
    ]
    for item in items:
        item['is_active'] = item['key'] == active_module
    return items

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
        'module_buttons': _module_buttons('buses'),
    }

    return render(request, 'core/bus_dashboard.html', context)

def _get_driver_rows():
    rows = []
    drivers = Driver.objects.order_by('id')

    for driver in drivers:
        current_trip = (
            Trip.objects.select_related(
                'schedule__conductor',
                'schedule__timetable__route',
            )
            .filter(schedule__driver=driver)
            .exclude(t_status='COMPLETED')
            .order_by('-actual_departure_time', '-id')
            .first()
        )

        if not current_trip:
            current_trip = (
                Trip.objects.select_related(
                    'schedule__conductor',
                    'schedule__timetable__route',
                )
                .filter(schedule__driver=driver)
                .order_by('-actual_departure_time', '-id')
                .first()
            )

        schedule_label = '-'
        conductor_name = '-'

        if current_trip:
            schedule_label = str(current_trip.schedule)
            if current_trip.schedule.conductor:
                conductor_name = current_trip.schedule.conductor.conductor_name

        rows.append(
            {
                'driver': driver,
                'current_trip': schedule_label,
                'conductor_name': conductor_name,
            }
        )

    return rows


def driver_dashboard(request):
    selected_driver_id = request.GET.get('driver')
    driver_rows = _get_driver_rows()

    selected_driver = driver_rows[0]['driver'] if driver_rows else None
    if selected_driver_id:
        selected_driver = get_object_or_404(Driver, id=selected_driver_id)

    context = {
        'driver_rows': driver_rows,
        'selected_driver': selected_driver,
        'total_drivers': Driver.objects.count(),
        'available_drivers': Driver.objects.filter(driver_status='AVAILABLE').count(),
        'on_route_drivers': Driver.objects.filter(driver_status='ON_ROUTE').count(),
        'off_duty_drivers': Driver.objects.filter(driver_status='OFF_DUTY').count(),
        'module_buttons': _module_buttons('drivers'),
    }
    return render(request, 'core/driver_dashboard.html', context)


def _get_conductor_rows():
    rows = []
    conductors = Conductor.objects.order_by('id')

    for conductor in conductors:
        current_trip = (
            Trip.objects.select_related(
                'schedule__driver',
                'schedule__timetable__route',
            )
            .filter(schedule__conductor=conductor)
            .exclude(t_status='COMPLETED')
            .order_by('-actual_departure_time', '-id')
            .first()
        )

        if not current_trip:
            current_trip = (
                Trip.objects.select_related(
                    'schedule__driver',
                    'schedule__timetable__route',
                )
                .filter(schedule__conductor=conductor)
                .order_by('-actual_departure_time', '-id')
                .first()
            )

        schedule_label = '-'
        driver_name = '-'

        if current_trip:
            schedule_label = str(current_trip.schedule)
            if current_trip.schedule.driver:
                driver_name = current_trip.schedule.driver.driver_name

        rows.append(
            {
                'conductor': conductor,
                'current_trip': schedule_label,
                'driver_name': driver_name,
            }
        )

    return rows


def conductor_dashboard(request):
    selected_conductor_id = request.GET.get('conductor')
    conductor_rows = _get_conductor_rows()

    selected_conductor = conductor_rows[0]['conductor'] if conductor_rows else None
    if selected_conductor_id:
        selected_conductor = get_object_or_404(Conductor, id=selected_conductor_id)

    context = {
        'conductor_rows': conductor_rows,
        'selected_conductor': selected_conductor,
        'total_conductors': Conductor.objects.count(),
        'available_conductors': Conductor.objects.filter(conductor_status='AVAILABLE').count(),
        'on_duty_conductors': Conductor.objects.filter(conductor_status='ON_DUTY').count(),
        'off_duty_conductors': Conductor.objects.filter(conductor_status='OFF_DUTY').count(),
        'module_buttons': _module_buttons('conductors'),
    }
    return render(request, 'core/conductor_dashboard.html', context)


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
        {'form': form, 'bus': bus, 'module_buttons': _module_buttons('buses')},
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
        {'form': form, 'module_buttons': _module_buttons('buses')},
    )


def manage_driver(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id)

    if request.method == 'POST':
        if 'delete_driver' in request.POST:
            driver.delete()
            return redirect('driver_dashboard')

        form = DriverForm(request.POST, request.FILES, instance=driver)
        if form.is_valid():
            form.save()
            return redirect(f"{reverse('driver_dashboard')}?driver={driver.id}")
    else:
        form = DriverForm(instance=driver)

    return render(
        request,
        'core/manage_driver.html',
        {'form': form, 'driver': driver, 'module_buttons': _module_buttons('drivers')},
    )


def add_driver(request):
    if request.method == 'POST':
        form = DriverForm(request.POST, request.FILES)
        if form.is_valid():
            created_driver = form.save()
            return redirect(f"{reverse('driver_dashboard')}?driver={created_driver.id}")
    else:
        form = DriverForm()

    return render(
        request,
        'core/add_driver.html',
        {'form': form, 'module_buttons': _module_buttons('drivers')},
    )


def manage_conductor(request, conductor_id):
    conductor = get_object_or_404(Conductor, id=conductor_id)

    if request.method == 'POST':
        if 'delete_conductor' in request.POST:
            conductor.delete()
            return redirect('conductor_dashboard')

        form = ConductorForm(request.POST, request.FILES, instance=conductor)
        if form.is_valid():
            form.save()
            return redirect(f"{reverse('conductor_dashboard')}?conductor={conductor.id}")
    else:
        form = ConductorForm(instance=conductor)

    return render(
        request,
        'core/manage_conductor.html',
        {'form': form, 'conductor': conductor, 'module_buttons': _module_buttons('conductors')},
    )


def add_conductor(request):
    if request.method == 'POST':
        form = ConductorForm(request.POST, request.FILES)
        if form.is_valid():
            created_conductor = form.save()
            return redirect(f"{reverse('conductor_dashboard')}?conductor={created_conductor.id}")
    else:
        form = ConductorForm()

    return render(
        request,
        'core/add_conductor.html',
        {'form': form, 'module_buttons': _module_buttons('conductors')},
    )


def route_dashboard(request):
    routes = Route.objects.order_by('route_number')
    context = {
        'routes': routes,
        'module_buttons': _module_buttons('manage_routes'),
    }
    return render(request, 'core/route_dashboard.html', context)

def add_route(request):
    if request.method == 'POST':
        form = RouteForm(request.POST)
        if form.is_valid():
            created_route = form.save()
            return redirect('manage_route_stops', route_id=created_route.id)
    else:
        form = RouteForm()

    return render(
        request,
        'core/add_route.html',
        {'form': form, 'module_buttons': _module_buttons('manage_routes')},
    )


def manage_route_stops(request, route_id):
    route = get_object_or_404(Route, id=route_id)

    if request.method == 'POST':
        stop_id_list = request.POST.getlist('ordered_stop_ids')

        RouteStop.objects.filter(route=route).delete()
        route_stops_to_create = []
        for index, stop_id in enumerate(stop_id_list, start=1):
            stop = Stop.objects.filter(id=stop_id).first()
            if stop:
                route_stops_to_create.append(RouteStop(route=route, stop=stop, order=index))
        RouteStop.objects.bulk_create(route_stops_to_create)
        return redirect('manage_route_stops', route_id=route.id)

    route_stops = (
        RouteStop.objects.select_related('stop')
        .filter(route=route)
        .order_by('order')
    )

    context = {
        'route': route,
        'route_stops': route_stops,
        'all_stops': Stop.objects.order_by('stop_name'),
        'module_buttons': _module_buttons('manage_routes'),
    }
    return render(request, 'core/manage_route_stops.html', context)

def timetable_dashboard(request):
    if request.method == 'POST' and 'delete_timetable' in request.POST:
        timetable_id = request.POST.get('timetable_id')
        timetable = get_object_or_404(TimeTable, id=timetable_id)
        timetable.delete()
        return redirect('timetable_dashboard')

    timetables = TimeTable.objects.select_related('route').order_by(
        'route__route_number', 'day_of_week', 'departure_time'
    )
    routes_covered = timetables.values('route').distinct().count()

    context = {
        'timetables': timetables,
        'total_timetables': timetables.count(),
        'outbound_count': timetables.filter(direction='OUTBOUND').count(),
        'return_count': timetables.filter(direction='RETURN').count(),
        'routes_count': routes_covered,
        'module_buttons': _module_buttons('view_timetable'),
    }
    return render(request, 'core/timetable_dashboard.html', context)


def add_timetable(request):
    if request.method == 'POST':
        form = TimeTableForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('timetable_dashboard')
    else:
        form = TimeTableForm()

    return render(
        request,
        'core/add_timetable.html',
        {'form': form, 'module_buttons': _module_buttons('view_timetable')},
    )


def add_stop(request, route_id):
    route = get_object_or_404(Route, id=route_id)

    if request.method == 'POST':
        form = StopForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('manage_route_stops', route_id=route.id)
    else:
        form = StopForm()

    return render(
        request,
        'core/add_stop.html',
        {
            'form': form,
            'route': route,
            'module_buttons': _module_buttons('manage_routes'),
        },
    )

def scheduling_dashboard(request):
    if request.method == 'POST' and 'delete_schedule' in request.POST:
        schedule_id = request.POST.get('schedule_id')
        schedule = get_object_or_404(Schedule, id=schedule_id)
        schedule.delete()
        return redirect('scheduling_dashboard')

    schedules = Schedule.objects.select_related(
        'timetable__route', 'bus', 'driver', 'conductor'
    ).order_by('-date', 'timetable__departure_time')

    context = {
        'schedules': schedules,
        'total_schedules': schedules.count(),
        'scheduled_count': schedules.filter(status='SCHEDULED').count(),
        'completed_count': schedules.filter(status='COMPLETED').count(),
        'cancelled_count': schedules.filter(status='CANCELLED').count(),
        'module_buttons': _module_buttons('scheduling'),
    }
    return render(request, 'core/scheduling_dashboard.html', context)


def add_schedule(request):
    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('scheduling_dashboard')
    else:
        form = ScheduleForm()

    return render(
        request,
        'core/add_schedule.html',
        {'form': form, 'module_buttons': _module_buttons('scheduling')},
    )


def maintenance_dashboard(request):
    if request.method == 'POST' and 'delete_maintenance' in request.POST:
        record_id = request.POST.get('record_id')
        record = get_object_or_404(BusMaintenance, id=record_id)
        record.delete()
        return redirect('maintenance_dashboard')

    maintenance_records = BusMaintenance.objects.select_related('bus').order_by(
        '-service_date', '-created_at'
    )

    context = {
        'maintenance_records': maintenance_records,
        'total_records': maintenance_records.count(),
        'due_records': maintenance_records.filter(next_service_due_mileage__isnull=False).count(),
        'module_buttons': _module_buttons('maintenance'),
    }
    return render(request, 'core/maintenance_dashboard.html', context)


def get_outbound_for_return(request):
    """
    AJAX endpoint: given a RETURN timetable ID and a date, returns the
    matching outbound schedule's bus/driver/conductor (if the gap is <= 1 hour).
    """
    from datetime import datetime, timedelta
    from django.http import JsonResponse

    timetable_id = request.GET.get('timetable_id')
    date_str = request.GET.get('date')

    if not timetable_id or not date_str:
        return JsonResponse({'match': False})

    try:
        return_tt = TimeTable.objects.get(id=timetable_id, direction='RETURN')
        schedule_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (TimeTable.DoesNotExist, ValueError):
        return JsonResponse({'match': False})

    outbound_timetables = TimeTable.objects.filter(
        route=return_tt.route,
        direction='OUTBOUND',
        day_of_week=return_tt.day_of_week,
    )

    matching_outbound_tt = None
    for tt in outbound_timetables:
        outbound_arrival = datetime.combine(schedule_date, tt.arrival_time)
        return_dep = datetime.combine(schedule_date, return_tt.departure_time)
        gap = return_dep - outbound_arrival
        if timedelta(0) <= gap <= timedelta(hours=1):
            matching_outbound_tt = tt
            break

    if not matching_outbound_tt:
        return JsonResponse({'match': False})

    outbound_schedule = Schedule.objects.filter(
        timetable=matching_outbound_tt,
        date=schedule_date,
    ).select_related('bus', 'driver', 'conductor').first()

    if not outbound_schedule:
        return JsonResponse({'match': False})

    return JsonResponse({
        'match': True,
        'bus_id': outbound_schedule.bus_id,
        'bus_label': str(outbound_schedule.bus) if outbound_schedule.bus else '',
        'driver_id': outbound_schedule.driver_id,
        'driver_label': str(outbound_schedule.driver) if outbound_schedule.driver else '',
        'conductor_id': outbound_schedule.conductor_id,
        'conductor_label': str(outbound_schedule.conductor) if outbound_schedule.conductor else '',
        'outbound_departure': str(matching_outbound_tt.departure_time),
        'outbound_arrival': str(matching_outbound_tt.arrival_time),
    })


def add_maintenance(request):
    if request.method == 'POST':
        form = BusMaintenanceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('maintenance_dashboard')
    else:
        form = BusMaintenanceForm()

    return render(
        request,
        'core/add_maintenance.html',
        {'form': form, 'module_buttons': _module_buttons('maintenance')},
    )
