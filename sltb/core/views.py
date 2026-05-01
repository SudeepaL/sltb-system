import csv
from django.db import models
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from functools import wraps
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import urlencode

from .forms import BusForm, BusMaintenanceForm, ConductorForm, DriverForm, RouteForm, ScheduleForm, StopForm, TimeTableForm
from .models import (
    Bus, BusMaintenance, BusRefuelLog, Conductor, DepotFuelTank,
    Driver, Route, Schedule, RouteStop, Stop, StaffAttendance, TimeTable, Trip,
    TripRevenue, PassengerBoardingLog,
)
from .revenue_simulator import simulate_trip_revenue, _is_peak



ROLE_CREDENTIALS = {
    'admin': {'username': 'admin', 'password': 'admin123', 'label': 'Admin'},
    'route_manager': {'username': 'routemgr', 'password': 'route123', 'label': 'Route Manager'},
    'maintenance_manager': {'username': 'maintainmgr', 'password': 'maintain123', 'label': 'Maintenance Manager'},
}

ROLE_MODULE_ACCESS = {
    'admin': {
        'buses': 'full',
        'drivers': 'full',
        'conductors': 'full',
        'manage_routes': 'view',
        'view_timetable': 'view',
        'scheduling': 'view',
        'fuel_usage': 'full',
        'maintenance': 'view',
        'current_trips': 'full',
        'revenue': 'full',
        'maintenance_reports': 'full',
        'admin_attendance': 'full',
    },
    'route_manager': {
        'manage_routes': 'full',
        'view_timetable': 'full',
        'scheduling': 'full',
    },
    'maintenance_manager': {
        'maintenance': 'full',
        'maintenance_reports': 'full',
    },
}


def _current_role(request):
    role = request.session.get('user_role')
    return role if role in ROLE_MODULE_ACCESS else None


def _has_access(request, module_key, required='view'):
    role = _current_role(request)
    if not role:
        return False

    access = ROLE_MODULE_ACCESS[role].get(module_key)
    if required == 'view':
        return access in {'view', 'full'}
    return access == 'full'


def _authorize(request, module_key, required='view'):
    if not _current_role(request):
        return redirect('login')
    if not _has_access(request, module_key, required=required):
        return HttpResponseForbidden('Access denied for this module.')
    return None


def _role_required(module_key, required='view'):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            blocked = _authorize(request, module_key, required=required)
            if blocked:
                return blocked
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def login_view(request):
    error_message = ''
    if request.method == 'POST':
        selected_role = request.POST.get('role')
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        credential = ROLE_CREDENTIALS.get(selected_role)
        if credential and username == credential['username'] and password == credential['password']:
            request.session['user_role'] = selected_role
            request.session['display_role'] = credential['label']
            return redirect('role_dashboard')
        error_message = 'Invalid role, username, or password.'

    return render(request, 'core/login.html', {'error_message': error_message})


def logout_view(request):
    request.session.flush()
    return redirect('login')


def home(request):
    role = _current_role(request)
    if not role:
        return redirect('login')
    return redirect('role_dashboard')


def role_dashboard(request):
    role = _current_role(request)
    if not role:
        return redirect('login')

    today = timezone.now().date()
    ctx = {
        'role': role,
        'display_role': request.session.get('display_role', ''),
        'module_buttons': _module_buttons(request, 'dashboard'),
        'logout_url': reverse('logout'),
    }

    if role == 'admin':
        buses         = Bus.objects.all()
        total_buses   = buses.count()
        avail_buses   = buses.filter(status='AVAILABLE').count()
        onroute_buses = buses.filter(status='ON_ROUTE').count()
        maint_buses   = buses.filter(status='MAINTENANCE').count()

        trips_today      = Trip.objects.filter(schedule__date=today)
        completed_trips  = trips_today.filter(t_status='COMPLETED').count()
        ongoing_trips    = trips_today.filter(t_status='ONGOING').count()
        delayed_trips    = trips_today.filter(t_status='DELAYED').count()

        drivers_on_route   = Driver.objects.filter(driver_status='ON_ROUTE').count()
        conductors_on_duty = Conductor.objects.filter(conductor_status='ON_DUTY').count()

        from django.db.models import Sum
        revenue_today = TripRevenue.objects.filter(
            trip__schedule__date=today
        ).aggregate(total=Sum('total_revenue'))['total'] or 0

        tank         = DepotFuelTank.get_tank()
        active_maint = BusMaintenance.objects.filter(maintenance_status='IN_SERVICE').count()

        overdue_buses = Bus.objects.filter(
            maintenance_records__maintenance_status='COMPLETED',
            mileage__gt=models.F('maintenance_records__next_service_due_mileage'),
        ).distinct().count()

        recent_trips = Trip.objects.select_related(
            'schedule__bus', 'schedule__timetable__route'
        ).filter(schedule__date=today).order_by('-schedule__timetable__departure_time')[:5]

        attendance_today = StaffAttendance.objects.select_related(
            'driver', 'conductor'
        ).filter(clock_in_time__date=today).order_by('-clock_in_time')[:10]

        ctx.update({
            'total_buses': total_buses, 'avail_buses': avail_buses,
            'onroute_buses': onroute_buses, 'maint_buses': maint_buses,
            'trips_today': trips_today.count(), 'completed_trips': completed_trips,
            'ongoing_trips': ongoing_trips, 'delayed_trips': delayed_trips,
            'drivers_on_route': drivers_on_route, 'conductors_on_duty': conductors_on_duty,
            'revenue_today': revenue_today, 'tank': tank,
            'tank_pct': round(tank.percentage()),
            'active_maint': active_maint, 'overdue_buses': overdue_buses,
            'recent_trips': recent_trips,
            'attendance_today': attendance_today,
        })

    elif role == 'route_manager':
        routes        = Route.objects.all()
        total_routes  = routes.count()
        timetables    = TimeTable.objects.all()
        total_tt      = timetables.count()
        outbound_tt   = timetables.filter(direction='OUTBOUND').count()
        return_tt     = timetables.filter(direction='RETURN').count()

        today_scheds     = Schedule.objects.filter(date=today)
        total_today      = today_scheds.count()
        unassigned_today = today_scheds.filter(
            models.Q(bus=None) | models.Q(driver=None) | models.Q(conductor=None)
        ).count()
        assigned_today   = total_today - unassigned_today
        routes_no_tt     = routes.filter(timetable__isnull=True).count()

        problem_schedules = Schedule.objects.select_related(
            'timetable__route', 'bus', 'driver', 'conductor'
        ).filter(date=today).filter(
            models.Q(bus=None) | models.Q(driver=None) | models.Q(conductor=None)
        )[:5]

        ctx.update({
            'total_routes': total_routes, 'total_tt': total_tt,
            'outbound_tt': outbound_tt, 'return_tt': return_tt,
            'total_today': total_today, 'assigned_today': assigned_today,
            'unassigned_today': unassigned_today, 'routes_no_tt': routes_no_tt,
            'problem_schedules': problem_schedules,
        })

    elif role == 'maintenance_manager':
        from django.db.models import Sum
        month_start = today.replace(day=1)

        active_jobs    = BusMaintenance.objects.filter(maintenance_status='IN_SERVICE').select_related('bus')
        active_count   = active_jobs.count()

        completed_qs     = BusMaintenance.objects.filter(
            maintenance_status='COMPLETED',
            actual_completion_date__date__gte=month_start,
        )
        completed_count  = completed_qs.count()
        cost_this_month  = completed_qs.aggregate(total=Sum('actual_cost'))['total'] or 0

        overdue_qs    = Bus.objects.filter(
            maintenance_records__maintenance_status='COMPLETED',
            mileage__gt=models.F('maintenance_records__next_service_due_mileage'),
        ).distinct()
        overdue_count = overdue_qs.count()

        ctx.update({
            'active_jobs': active_jobs, 'active_count': active_count,
            'completed_count': completed_count, 'cost_this_month': cost_this_month,
            'overdue_count': overdue_count, 'overdue_buses': overdue_qs[:5],
            'month_name': today.strftime('%B'),
        })

    return render(request, 'core/role_dashboard.html', ctx)


MAINTENANCE_CHATBOT_RULES = [
    {
        'keywords': ['engine overheating', 'overheating', 'temperature warning', 'coolant leak'],
        'title': 'Engine Overheating',
        'recommendations': [
            'Check coolant level and inspect for visible leaks around hoses, radiator, and water pump.',
            'Inspect radiator fan operation and fan relay/fuse condition.',
            'Pressure-test the cooling system and replace weak hose clamps or damaged hoses.',
            'If overheating persists after coolant top-up, inspect thermostat and water pump flow.',
        ],
    },
    {
        'keywords': ['brake', 'spongy pedal', 'brake noise', 'poor braking'],
        'title': 'Brake System Issue',
        'recommendations': [
            'Inspect brake fluid level and check for line or caliper leaks.',
            'Inspect pad/shoe wear and disc/drum condition for scoring or glazing.',
            'Bleed brake lines if pedal feels soft or spongy.',
            'Test parking brake function and adjust linkage if travel is excessive.',
        ],
    },
    {
        'keywords': ['battery', 'not starting', 'won’t start', 'wont start', 'starter', 'alternator'],
        'title': 'Starting / Electrical Issue',
        'recommendations': [
            'Measure battery voltage and load-test the battery before replacement.',
            'Check alternator charging output and belt tension.',
            'Inspect starter motor cable terminals for corrosion/looseness.',
            'Check ignition and starter relay circuits for intermittent faults.',
        ],
    },
    {
        'keywords': ['smoke', 'black smoke', 'white smoke', 'blue smoke'],
        'title': 'Abnormal Exhaust Smoke',
        'recommendations': [
            'For black smoke, inspect air filter restriction and injector spray quality.',
            'For white smoke, inspect coolant ingress and compression balance.',
            'For blue smoke, inspect turbo seals and engine oil consumption.',
            'Run injector calibration/diagnostics and verify fuel quality.',
        ],
    },
    {
        'keywords': ['ac', 'air conditioning', 'no cooling', 'weak cooling'],
        'title': 'HVAC Cooling Issue',
        'recommendations': [
            'Check refrigerant pressure and inspect for gas leaks.',
            'Inspect compressor clutch engagement and electrical supply.',
            'Clean condenser fins and verify condenser fan operation.',
            'Inspect cabin filters and blower motor airflow performance.',
        ],
    },
]


def _maintenance_recommendations(issue_text):
    issue = (issue_text or '').strip().lower()
    if not issue:
        return {
            'category': 'No issue provided',
            'recommendations': ['Please describe the bus issue so the assistant can suggest repair options.'],
        }

    for rule in MAINTENANCE_CHATBOT_RULES:
        if any(keyword in issue for keyword in rule['keywords']):
            return {
                'category': rule['title'],
                'recommendations': rule['recommendations'],
            }

    return {
        'category': 'General Diagnostic Suggestion',
        'recommendations': [
            'Run a full visual inspection and record fault symptoms (noise, vibration, warning lamps).',
            'Scan for ECU/diagnostic trouble codes and prioritize active faults.',
            'Check fluid levels (engine oil, coolant, brake fluid, transmission) and leak points.',
            'Perform a short road test after repairs to confirm issue resolution.',
        ],
    }

def _module_buttons(request, active_module):
    role = _current_role(request)
    if not role:
        return []

    # Dashboard is always first for every role
    visible_items = [
        {
            'label': 'Dashboard',
            'url': reverse('role_dashboard'),
            'key': 'dashboard',
            'is_active': active_module == 'dashboard',
        }
    ]

    items = [
        {'label': 'Buses', 'url': reverse('bus_dashboard'), 'key': 'buses'},
        {'label': 'Drivers', 'url': reverse('driver_dashboard'), 'key': 'drivers'},
        {'label': 'Conductors', 'url': reverse('conductor_dashboard'), 'key': 'conductors'},
        {'label': 'Manage Routes', 'url': reverse('route_dashboard'), 'key': 'manage_routes'},
        {'label': 'Manage Timetables', 'url': reverse('timetable_dashboard'), 'key': 'view_timetable'},
        {'label': 'Manage Schedules', 'url': reverse('scheduling_dashboard'), 'key': 'scheduling'},
        {'label': 'Fuel Usage', 'url': reverse('fuel_dashboard'), 'key': 'fuel_usage'},
        {'label': 'Maintenance', 'url': reverse('admin_maintenance_overview') if role == 'admin' else reverse('maintenance_dashboard'), 'key': 'maintenance'},
        {'label': 'Current Trips', 'url': reverse('bus_trip_welcome'), 'key': 'current_trips'},
        {'label': 'Revenue', 'url': reverse('revenue_dashboard'), 'key': 'revenue'},
        {'label': 'Attendance', 'url': reverse('attendance_dashboard'), 'key': 'admin_attendance'},
    ]

    for item in items:
        if _has_access(request, item['key'], required='view'):
            item['is_active'] = item['key'] == active_module
            visible_items.append(item)

    return visible_items


# ── Revenue helpers ───────────────────────────────────────────────────────────

def _run_simulation(trip):
    """
    Run the passenger simulation for *trip* and persist the results.
    Idempotent: if a TripRevenue already exists it is replaced.
    Returns the TripRevenue instance.
    """
    TripRevenue.objects.filter(trip=trip).delete()

    result = simulate_trip_revenue(trip)

    trip_revenue = TripRevenue.objects.create(
        trip=trip,
        total_passengers=result['total_passengers'],
        total_revenue=result['total_revenue'],
        is_simulated=True,
    )

    PassengerBoardingLog.objects.bulk_create([
        PassengerBoardingLog(
            trip_revenue=trip_revenue,
            stop_name=s['stop_name'],
            stop_order=s['stop_order'],
            passengers_boarded=s['passengers_boarded'],
            passengers_alighted=s['passengers_alighted'],
            fare_per_passenger=s['fare_per_passenger'],
            stop_revenue=s['stop_revenue'],
            cumulative_passengers=s['cumulative_passengers'],
            cumulative_revenue=s['cumulative_revenue'],
        )
        for s in result['stops']
    ])

    return trip_revenue


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
            .filter(t_status__in=['ONGOING', 'DELAYED'])
            .order_by('-actual_departure_time', '-id')
            .first()
        )

        schedule_label = '-'
        route_number = '-'
        driver_name = '-'
        conductor_name = '-'

        if current_trip:
            route = current_trip.schedule.timetable.route
            schedule_label = f'{route.start_location}-{route.end_location}'
            route_number = route.route_number
            if current_trip.schedule.driver:
                driver_name = current_trip.schedule.driver.driver_name
            if current_trip.schedule.conductor:
                conductor_name = current_trip.schedule.conductor.conductor_name

        rows.append(
            {
                'bus': bus,
                'current_route': schedule_label,
                'current_route_number': route_number,
                'driver_name': driver_name,
                'conductor_name': conductor_name,
            }
        )

    return rows

@_role_required('buses', 'view')
def bus_dashboard(request):
    selected_bus_id = request.GET.get('bus')
    bus_rows = _get_bus_trip_rows()
    capacity_filter = request.GET.get('capacity_filter', '')
    bus_type_filter = request.GET.get('bus_type_filter', '')
    status_filter = request.GET.get('status_filter', '')
    route_filter = request.GET.get('route_filter', '').strip()

    if capacity_filter == '30_40':
        bus_rows = [row for row in bus_rows if 30 <= row['bus'].capacity <= 40]
    elif capacity_filter == '40_50':
        bus_rows = [row for row in bus_rows if 40 <= row['bus'].capacity <= 50]

    if bus_type_filter in {'AC', 'NON_AC'}:
        bus_rows = [row for row in bus_rows if row['bus'].bus_type == bus_type_filter]

    valid_statuses = {choice[0] for choice in Bus.STATUS_CHOICES}
    if status_filter in valid_statuses:
        bus_rows = [row for row in bus_rows if row['bus'].status == status_filter]

    if route_filter:
        bus_rows = [
            row for row in bus_rows
            if row['current_route_number'] != '-' and route_filter.lower() in row['current_route_number'].lower()
        ]

    selected_bus = bus_rows[0]['bus'] if bus_rows else None
    if selected_bus_id:
        selected_bus = next((row['bus'] for row in bus_rows if str(row['bus'].id) == selected_bus_id), None)

    on_route_count = Bus.objects.filter(status='ON_ROUTE').count()
    maintenance_count = Bus.objects.filter(status='MAINTENANCE').count()
    filter_query = urlencode(
        {
            'capacity_filter': capacity_filter,
            'bus_type_filter': bus_type_filter,
            'status_filter': status_filter,
            'route_filter': route_filter,
        }
    )

    context = {
        'bus_rows': bus_rows,
        'selected_bus': selected_bus,
        'total_buses': Bus.objects.count(),
        'available_buses': Bus.objects.filter(status='AVAILABLE').count(),
        'on_route_buses': on_route_count,
        'maintenance_buses': maintenance_count,
        'module_buttons': _module_buttons(request, 'buses'),
        'capacity_filter': capacity_filter,
        'bus_type_filter': bus_type_filter,
        'status_filter': status_filter,
        'route_filter': route_filter,
        'filter_query': filter_query,
    }

    return render(request, 'core/bus_dashboard.html', context)

def _get_driver_rows(gender_filter=None, status_filter=None):
    rows = []
    drivers = Driver.objects.order_by('id')

    if gender_filter:
        drivers = drivers.filter(gender=gender_filter)
    if status_filter:
        drivers = drivers.filter(driver_status=status_filter)

    for driver in drivers:
        current_trip = (
            Trip.objects.select_related(
                'schedule__conductor',
                'schedule__timetable__route',
            )
            .filter(schedule__driver=driver)
            .filter(t_status__in=['ONGOING', 'DELAYED'])
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

@_role_required('drivers', 'view')
def driver_dashboard(request):
    selected_driver_id = request.GET.get('driver')
    gender_filter = request.GET.get('gender_filter', '')
    status_filter = request.GET.get('status_filter', '')

    driver_rows = _get_driver_rows(
        gender_filter=gender_filter or None,
        status_filter=status_filter or None,
    )

    selected_driver = driver_rows[0]['driver'] if driver_rows else None
    if selected_driver_id:
        selected_driver = get_object_or_404(Driver, id=selected_driver_id)

    filter_params = []
    if gender_filter:
        filter_params.append(f'gender_filter={gender_filter}')
    if status_filter:
        filter_params.append(f'status_filter={status_filter}')
    filter_query = '&'.join(filter_params)

    context = {
        'driver_rows': driver_rows,
        'selected_driver': selected_driver,
        'total_drivers': Driver.objects.count(),
        'available_drivers': Driver.objects.filter(driver_status='AVAILABLE').count(),
        'on_route_drivers': Driver.objects.filter(driver_status='ON_ROUTE').count(),
        'off_duty_drivers': Driver.objects.filter(driver_status='OFF_DUTY').count(),
        'module_buttons': _module_buttons(request, 'drivers'),
        'gender_filter': gender_filter,
        'status_filter': status_filter,
        'filter_query': filter_query,
    }
    return render(request, 'core/driver_dashboard.html', context)


def _get_conductor_rows(gender_filter=None, status_filter=None):
    rows = []
    conductors = Conductor.objects.order_by('id')

    if gender_filter:
        conductors = conductors.filter(c_gender=gender_filter)
    if status_filter:
        conductors = conductors.filter(conductor_status=status_filter)

    for conductor in conductors:
        current_trip = (
            Trip.objects.select_related(
                'schedule__driver',
                'schedule__timetable__route',
            )
            .filter(schedule__conductor=conductor)
            .filter(t_status__in=['ONGOING', 'DELAYED'])
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

@_role_required('conductors', 'view')
def conductor_dashboard(request):
    selected_conductor_id = request.GET.get('conductor')
    gender_filter = request.GET.get('gender_filter', '')
    status_filter = request.GET.get('status_filter', '')

    conductor_rows = _get_conductor_rows(
        gender_filter=gender_filter or None,
        status_filter=status_filter or None,
    )

    selected_conductor = conductor_rows[0]['conductor'] if conductor_rows else None
    if selected_conductor_id:
        selected_conductor = get_object_or_404(Conductor, id=selected_conductor_id)

    filter_params = []
    if gender_filter:
        filter_params.append(f'gender_filter={gender_filter}')
    if status_filter:
        filter_params.append(f'status_filter={status_filter}')
    filter_query = '&'.join(filter_params)

    context = {
        'conductor_rows': conductor_rows,
        'selected_conductor': selected_conductor,
        'total_conductors': Conductor.objects.count(),
        'available_conductors': Conductor.objects.filter(conductor_status='AVAILABLE').count(),
        'on_duty_conductors': Conductor.objects.filter(conductor_status='ON_DUTY').count(),
        'off_duty_conductors': Conductor.objects.filter(conductor_status='OFF_DUTY').count(),
        'module_buttons': _module_buttons(request, 'conductors'),
        'gender_filter': gender_filter,
        'status_filter': status_filter,
        'filter_query': filter_query,
    }
    return render(request, 'core/conductor_dashboard.html', context)


# ── AJAX detail endpoints ─────────────────────────────────────────────────────

@_role_required('buses', 'view')
def bus_detail_json(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)
    data = {
        'id': bus.id,
        'bus_number': bus.bus_number,
        'bus_code': bus.bus_code,
        'model': bus.model or '-',
        'bus_type': bus.get_bus_type_display(),
        'fuel_capacity_liters': bus.fuel_capacity_liters,
        'current_fuel_liters': bus.current_fuel_liters,
        'capacity': bus.capacity,
        'mileage': bus.mileage,
        'status': bus.get_status_display(),
        'depot': str(bus.depot) if bus.depot else '-',
        'fuel_efficiency': bus.fuel_efficiency_km_per_liter,
        'image_url': bus.image.url if bus.image else None,
        'manage_url': reverse('manage_bus', args=[bus.id]),
    }
    return JsonResponse(data)


@_role_required('drivers', 'view')
def driver_detail_json(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id)
    data = {
        'id': driver.id,
        'driver_name': driver.driver_name,
        'nic_number': driver.nic_number,
        'driving_license_number': driver.driving_license_number,
        'dob': str(driver.dob) if driver.dob else '-',
        'gender': driver.get_gender_display(),
        'phone_number': driver.phone_number,
        'email': driver.email or '-',
        'driver_address': driver.driver_address or '-',
        'status': driver.get_driver_status_display(),
        'image_url': driver.driver_id_image.url if driver.driver_id_image else None,
        'manage_url': reverse('manage_driver', args=[driver.id]),
    }
    return JsonResponse(data)


@_role_required('conductors', 'view')
def conductor_detail_json(request, conductor_id):
    conductor = get_object_or_404(Conductor, id=conductor_id)
    data = {
        'id': conductor.id,
        'conductor_name': conductor.conductor_name,
        'c_nic_number': conductor.c_nic_number,
        'c_dob': str(conductor.c_dob) if conductor.c_dob else '-',
        'gender': conductor.get_c_gender_display(),
        'c_phone_number': conductor.c_phone_number,
        'c_email': conductor.c_email or '-',
        'conductor_address': conductor.conductor_address or '-',
        'status': conductor.get_conductor_status_display(),
        'image_url': conductor.conductor_id_image.url if conductor.conductor_id_image else None,
        'manage_url': reverse('manage_conductor', args=[conductor.id]),
    }
    return JsonResponse(data)


@_role_required('buses', 'full')
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
        {'form': form, 'bus': bus, 'module_buttons': _module_buttons(request, 'buses')},
    )


@_role_required('buses', 'full')
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
        {'form': form, 'module_buttons': _module_buttons(request, 'buses')},
    )


@_role_required('drivers', 'full')
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
        {'form': form, 'driver': driver, 'module_buttons': _module_buttons(request, 'drivers')},
    )


@_role_required('drivers', 'full')
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
        {'form': form, 'module_buttons': _module_buttons(request, 'drivers')},
    )


@_role_required('conductors', 'full')
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
        {'form': form, 'conductor': conductor, 'module_buttons': _module_buttons(request, 'conductors')},
    )


@_role_required('conductors', 'full')
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
        {'form': form, 'module_buttons': _module_buttons(request, 'conductors')},
    )


@_role_required('manage_routes', 'view')
def route_dashboard(request):
    routes = Route.objects.order_by('route_number')
    context = {
        'routes': routes,
        'module_buttons': _module_buttons(request, 'manage_routes'),
        'can_manage_routes': _has_access(request, 'manage_routes', required='full'),
    }
    return render(request, 'core/route_dashboard.html', context)

@_role_required('manage_routes', 'full')
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
        {'form': form, 'module_buttons': _module_buttons(request, 'manage_routes')},
    )


def manage_route_stops(request, route_id):
    route = get_object_or_404(Route, id=route_id)

    if request.method == 'POST':
        if not _has_access(request, 'manage_routes', required='full'):
            return HttpResponseForbidden('You have view-only access for route management.')
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
        'module_buttons': _module_buttons(request, 'manage_routes'),
        'can_manage_routes': _has_access(request, 'manage_routes', required='full'),
    }
    return render(request, 'core/manage_route_stops.html', context)

@_role_required('view_timetable', 'view')
def timetable_dashboard(request):
    if request.method == 'POST' and 'delete_timetable' in request.POST:
        if not _has_access(request, 'view_timetable', required='full'):
            return HttpResponseForbidden('You have view-only access for timetables.')
        timetable_id = request.POST.get('timetable_id')
        timetable = get_object_or_404(TimeTable, id=timetable_id)
        timetable.delete()
        return redirect('timetable_dashboard')

    route_filter = (request.GET.get('route_filter') or '').strip()
    day_filter = (request.GET.get('day_filter') or '').strip().lower()
    direction_filter = (request.GET.get('direction_filter') or '').strip().upper()
    departure_band_filter = (request.GET.get('departure_band_filter') or '').strip().lower()
    arrival_band_filter = (request.GET.get('arrival_band_filter') or '').strip().lower()

    timetables = TimeTable.objects.select_related('route')

    if route_filter:
        timetables = timetables.filter(route__route_number__icontains=route_filter)
    if day_filter:
        timetables = timetables.filter(day_of_week=day_filter)
    if direction_filter:
        timetables = timetables.filter(direction=direction_filter)

    time_band_ranges = {
        'morning': ('04:00', '11:59'),
        'afternoon': ('12:00', '15:59'),
        'evening': ('16:00', '19:29'),
        'night': ('19:30', '23:59'),
        'midnight': ('00:00', '03:59'),
    }

    if departure_band_filter in time_band_ranges:
        start_time, end_time = time_band_ranges[departure_band_filter]
        timetables = timetables.filter(departure_time__range=(start_time, end_time))
    if arrival_band_filter in time_band_ranges:
        start_time, end_time = time_band_ranges[arrival_band_filter]
        timetables = timetables.filter(arrival_time__range=(start_time, end_time))

    timetables = timetables.order_by('route__route_number', 'day_of_week', 'departure_time')
    routes_covered = timetables.values('route').distinct().count()

    context = {
        'timetables': timetables,
        'total_timetables': timetables.count(),
        'outbound_count': timetables.filter(direction='OUTBOUND').count(),
        'return_count': timetables.filter(direction='RETURN').count(),
        'routes_count': routes_covered,
        'route_filter': route_filter,
        'day_filter': day_filter,
        'direction_filter': direction_filter,
        'departure_band_filter': departure_band_filter,
        'arrival_band_filter': arrival_band_filter,
        'module_buttons': _module_buttons(request, 'view_timetable'),
        'can_manage_timetables': _has_access(request, 'view_timetable', required='full'),
    }
    return render(request, 'core/timetable_dashboard.html', context)


@_role_required('view_timetable', 'full')
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
        {'form': form, 'module_buttons': _module_buttons(request, 'view_timetable')},
    )

@_role_required('manage_routes', 'full')
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
            'module_buttons': _module_buttons(request, 'manage_routes'),
        },
    )

@_role_required('scheduling', 'view')
def scheduling_dashboard(request):
    if request.method == 'POST' and 'delete_schedule' in request.POST:
        if not _has_access(request, 'scheduling', required='full'):
            return HttpResponseForbidden('You have view-only access for schedules.')
        schedule_id = request.POST.get('schedule_id')
        schedule = get_object_or_404(Schedule, id=schedule_id)
        schedule.delete()
        return redirect('scheduling_dashboard')

    from datetime import date as date_today
    today = date_today.today()

    # Determine which view the user wants: today (default), past, or future
    view_mode = request.GET.get('view', 'today')

    all_schedules = Schedule.objects.select_related(
        'timetable__route', 'bus', 'driver', 'conductor'
    )

    if view_mode == 'past':
        schedules = all_schedules.filter(date__lt=today).order_by('-date', 'timetable__departure_time')
        view_title = 'Past Schedules'
    elif view_mode == 'future':
        schedules = all_schedules.filter(date__gt=today).order_by('date', 'timetable__departure_time')
        view_title = 'Future Schedules'
    else:
        view_mode = 'today'
        schedules = all_schedules.filter(date=today).order_by('timetable__departure_time')
        view_title = "Today's Schedules"

    context = {
        'schedules': schedules,
        'view_mode': view_mode,
        'view_title': view_title,
        'today': today,
        'total_schedules': schedules.count(),
        'scheduled_count': schedules.filter(status='SCHEDULED').count(),
        'ongoing_count': schedules.filter(status='ONGOING').count(),
        'delayed_count': schedules.filter(status='DELAYED').count(),
        'completed_count': schedules.filter(status='COMPLETED').count(),
        'cancelled_count': schedules.filter(status='CANCELLED').count(),
        'module_buttons': _module_buttons(request, 'scheduling'),
        'can_manage_schedules': _has_access(request, 'scheduling', required='full'),
    }
    return render(request, 'core/scheduling_dashboard.html', context)


@_role_required('scheduling', 'full')
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
        {'form': form, 'module_buttons': _module_buttons(request, 'scheduling')},
    )


@_role_required('scheduling', 'view')
def get_schedule_resource_data(request):
    """
    AJAX endpoint: returns buses, drivers, conductors with statuses,
    their schedules, fuel levels, and route experience counts for AI-assisted
    scheduling recommendations.
    """
    timetable_id = request.GET.get('timetable_id')
    date_str = request.GET.get('date')

    route_distance = None
    route_id = None
    direction = None

    if timetable_id:
        try:
            tt = TimeTable.objects.select_related('route').get(id=timetable_id)
            route_distance = tt.route.distance
            route_id = tt.route.id
            direction = tt.direction
        except TimeTable.DoesNotExist:
            pass

    # ── Fuel threshold logic ──────────────────────────────────────────────────
    def min_fuel_required(distance):
        if distance is None:
            return 0
        if distance > 100:
            return 100
        if distance > 60:
            return 120
        if distance > 18:
            return 70
        if distance > 10:
            return 50
        return 0

    min_fuel = min_fuel_required(route_distance)

    # ── Buses ─────────────────────────────────────────────────────────────────
    all_buses = Bus.objects.all().order_by('bus_code')
    bus_schedules_qs = Schedule.objects.select_related(
        'timetable__route', 'bus'
    ).exclude(status__in=['COMPLETED', 'CANCELLED']).order_by('date', 'timetable__departure_time')

    bus_schedule_map = {}
    for s in bus_schedules_qs:
        bid = s.bus_id
        if bid not in bus_schedule_map:
            bus_schedule_map[bid] = []
        bus_schedule_map[bid].append({
            'id': s.id,
            'date': str(s.date),
            'route': s.timetable.route.route_number,
            'departure': str(s.timetable.departure_time),
            'direction': s.timetable.direction,
            'status': s.status,
        })

    buses = []
    for bus in all_buses:
        fuel = bus.current_fuel_liters or 0
        meets_fuel = (fuel >= min_fuel) if min_fuel > 0 else True
        buses.append({
            'id': bus.id,
            'code': bus.bus_code,
            'number': bus.bus_number,
            'status': bus.status,
            'fuel': round(fuel, 1),
            'min_fuel': min_fuel,
            'meets_fuel': meets_fuel,
            'recommended_fuel': meets_fuel and bus.status == 'AVAILABLE',
            'schedules': bus_schedule_map.get(bus.id, []),
        })

    # Sort: available first, then by fuel desc
    buses.sort(key=lambda b: (
        0 if b['status'] == 'AVAILABLE' else 1,
        -b['fuel']
    ))

    # ── Drivers ───────────────────────────────────────────────────────────────
    all_drivers = Driver.objects.all().order_by('driver_name')
    driver_schedules_qs = Schedule.objects.select_related(
        'timetable__route', 'driver'
    ).filter(driver__isnull=False).exclude(
        status__in=['COMPLETED', 'CANCELLED']
    ).order_by('date', 'timetable__departure_time')

    driver_schedule_map = {}
    for s in driver_schedules_qs:
        did = s.driver_id
        if did not in driver_schedule_map:
            driver_schedule_map[did] = []
        driver_schedule_map[did].append({
            'id': s.id,
            'date': str(s.date),
            'route': s.timetable.route.route_number,
            'departure': str(s.timetable.departure_time),
            'direction': s.timetable.direction,
            'status': s.status,
        })

    # Route experience: count completed trips on the same route (both directions)
    driver_experience_map = {}
    if route_id:
        completed_schedules = Schedule.objects.filter(
            timetable__route_id=route_id,
            status='COMPLETED',
            driver__isnull=False,
        ).values('driver_id').annotate(trip_count=models.Count('id'))
        for row in completed_schedules:
            driver_experience_map[row['driver_id']] = row['trip_count']

    drivers = []
    for driver in all_drivers:
        exp = driver_experience_map.get(driver.id, 0)
        experienced = exp >= 10
        drivers.append({
            'id': driver.id,
            'name': driver.driver_name,
            'status': driver.driver_status,
            'experience': exp,
            'experienced': experienced,
            'recommended': experienced and driver.driver_status == 'AVAILABLE',
            'schedules': driver_schedule_map.get(driver.id, []),
        })

    # Sort: available + experienced first
    drivers.sort(key=lambda d: (
        0 if d['status'] == 'AVAILABLE' else 1,
        0 if d['experienced'] else 1,
        -d['experience']
    ))

    # ── Conductors ────────────────────────────────────────────────────────────
    all_conductors = Conductor.objects.all().order_by('conductor_name')
    conductor_schedules_qs = Schedule.objects.select_related(
        'timetable__route', 'conductor'
    ).filter(conductor__isnull=False).exclude(
        status__in=['COMPLETED', 'CANCELLED']
    ).order_by('date', 'timetable__departure_time')

    conductor_schedule_map = {}
    for s in conductor_schedules_qs:
        cid = s.conductor_id
        if cid not in conductor_schedule_map:
            conductor_schedule_map[cid] = []
        conductor_schedule_map[cid].append({
            'id': s.id,
            'date': str(s.date),
            'route': s.timetable.route.route_number,
            'departure': str(s.timetable.departure_time),
            'direction': s.timetable.direction,
            'status': s.status,
        })

    conductor_experience_map = {}
    if route_id:
        completed_conductor = Schedule.objects.filter(
            timetable__route_id=route_id,
            status='COMPLETED',
            conductor__isnull=False,
        ).values('conductor_id').annotate(trip_count=models.Count('id'))
        for row in completed_conductor:
            conductor_experience_map[row['conductor_id']] = row['trip_count']

    conductors = []
    for conductor in all_conductors:
        exp = conductor_experience_map.get(conductor.id, 0)
        experienced = exp >= 10
        conductors.append({
            'id': conductor.id,
            'name': conductor.conductor_name,
            'status': conductor.conductor_status,
            'experience': exp,
            'experienced': experienced,
            'recommended': experienced and conductor.conductor_status == 'AVAILABLE',
            'schedules': conductor_schedule_map.get(conductor.id, []),
        })

    conductors.sort(key=lambda c: (
        0 if c['status'] == 'AVAILABLE' else 1,
        0 if c['experienced'] else 1,
        -c['experience']
    ))

    return JsonResponse({
        'buses': buses,
        'drivers': drivers,
        'conductors': conductors,
        'route_distance': route_distance,
        'min_fuel': min_fuel,
    })


@_role_required('maintenance', 'view')
def maintenance_dashboard(request):
    buses = Bus.objects.order_by('bus_code')
    selected_bus_code = request.GET.get('bus_code', '')

    selected_bus = None
    service_history = []
    if selected_bus_code:
        selected_bus = Bus.objects.filter(bus_code=selected_bus_code).first()
        if selected_bus:
            service_history = BusMaintenance.objects.filter(bus=selected_bus).order_by('-service_date', '-created_at')

    if request.method == 'POST':
        if not _has_access(request, 'maintenance', required='full'):
            return HttpResponseForbidden('You have view-only access for maintenance.')
        if 'add_bus_to_service' in request.POST:
            bus_code = request.POST.get('bus_code_hidden', '')
            bus = Bus.objects.filter(bus_code=bus_code).first()
            if bus:
                BusMaintenance.objects.create(
                    bus=bus,
                    service_date=request.POST.get('service_date'),
                    mileage=request.POST.get('mileage') or 0,
                    service_history=request.POST.get('service_history', ''),
                    maintenance_details=request.POST.get('maintenance_details', ''),
                    next_service_due_mileage=request.POST.get('next_service_due_mileage') or None,
                    estimated_maintenance_duration=request.POST.get('estimated_maintenance_duration') or None,
                    estimated_cost=request.POST.get('estimated_cost') or None,
                    maintenance_status='IN_SERVICE',
                )
                bus.status = 'MAINTENANCE'
                bus.save(update_fields=['status'])
            return redirect(f"{reverse('maintenance_dashboard')}?bus_code={bus_code}")

    active_records = BusMaintenance.objects.select_related('bus').filter(
        maintenance_status='IN_SERVICE'
    ).order_by('-service_date', '-created_at')

    completed_records = BusMaintenance.objects.select_related('bus').filter(
        maintenance_status='COMPLETED'
    ).order_by('-actual_completion_date', '-created_at')

    filter_date_from = request.GET.get('filter_date_from', '')
    filter_date_to = request.GET.get('filter_date_to', '')
    if filter_date_from:
        completed_records = completed_records.filter(service_date__gte=filter_date_from)
    if filter_date_to:
        completed_records = completed_records.filter(service_date__lte=filter_date_to)

    context = {
        'buses': buses,
        'selected_bus': selected_bus,
        'selected_bus_code': selected_bus_code,
        'service_history': service_history,
        'active_records': active_records,
        'completed_records': completed_records,
        'filter_date_from': filter_date_from,
        'filter_date_to': filter_date_to,
        'module_buttons': _module_buttons(request, 'maintenance'),
        'can_manage_maintenance': _has_access(request, 'maintenance', required='full'),
    }
    return render(request, 'core/maintenance_dashboard.html', context)



@_role_required('maintenance', 'view')
def admin_maintenance_overview(request):
    """
    For admin users: renders the maintenance manager's dashboard view
    (role_dashboard.html with role='maintenance_manager' context),
    while keeping the admin's own navbar module buttons.
    """
    role = _current_role(request)
    if not role:
        return redirect('login')

    today = timezone.now().date()
    month_start = today.replace(day=1)

    from django.db.models import Sum

    active_jobs   = BusMaintenance.objects.filter(maintenance_status='IN_SERVICE').select_related('bus')
    active_count  = active_jobs.count()

    completed_qs    = BusMaintenance.objects.filter(
        maintenance_status='COMPLETED',
        actual_completion_date__date__gte=month_start,
    )
    completed_count = completed_qs.count()
    cost_this_month = completed_qs.aggregate(total=Sum('actual_cost'))['total'] or 0

    overdue_qs    = Bus.objects.filter(
        maintenance_records__maintenance_status='COMPLETED',
        mileage__gt=models.F('maintenance_records__next_service_due_mileage'),
    ).distinct()
    overdue_count = overdue_qs.count()

    ctx = {
        'role': 'maintenance_manager',
        'display_role': request.session.get('display_role', ''),
        'module_buttons': _module_buttons(request, 'maintenance'),
        'logout_url': reverse('logout'),
        'active_jobs': active_jobs,
        'active_count': active_count,
        'completed_count': completed_count,
        'cost_this_month': cost_this_month,
        'overdue_count': overdue_count,
        'overdue_buses': overdue_qs[:5],
        'month_name': today.strftime('%B'),
    }
    return render(request, 'core/role_dashboard.html', ctx)


@_role_required('maintenance_reports', 'view')
def maintenance_report_csv(request):
    """Generate a CSV report of completed maintenance records filtered by the same date range."""
    completed_records = BusMaintenance.objects.select_related('bus').filter(
        maintenance_status='COMPLETED'
    ).order_by('service_date')

    bus_code = request.GET.get('bus_code', '')
    filter_date_from = request.GET.get('filter_date_from', '')
    filter_date_to = request.GET.get('filter_date_to', '')

    if bus_code:
        completed_records = completed_records.filter(bus__bus_code=bus_code)
    if filter_date_from:
        completed_records = completed_records.filter(service_date__gte=filter_date_from)
    if filter_date_to:
        completed_records = completed_records.filter(service_date__lte=filter_date_to)

    # Build a descriptive filename
    filename_parts = ['maintenance_report']
    if filter_date_from:
        filename_parts.append(f'from_{filter_date_from}')
    if filter_date_to:
        filename_parts.append(f'to_{filter_date_to}')
    filename = '_'.join(filename_parts) + '.csv'

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Report header block
    writer.writerow(['SLTB Maintenance Report'])
    writer.writerow(['Generated on', timezone.now().strftime('%Y-%m-%d %H:%M')])
    if filter_date_from or filter_date_to:
        date_range = f"{filter_date_from or 'All'} to {filter_date_to or 'All'}"
        writer.writerow(['Date Range', date_range])
    else:
        writer.writerow(['Date Range', 'All Records'])
    if bus_code:
        writer.writerow(['Bus Filter', bus_code])
    writer.writerow([])  # blank line

    # Column headers
    writer.writerow([
        'Bus Code',
        'Service Date',
        'Est. Completion Date/Time',
        'Actual Completion Date/Time',
        'Est. Cost (LKR)',
        'Actual Cost (LKR)',
    ])

    total_actual_cost = Decimal('0.00')

    for record in completed_records:
        est_duration = (
            record.estimated_maintenance_duration.strftime('%Y-%m-%d %H:%M')
            if record.estimated_maintenance_duration else ''
        )
        actual_completion = (
            record.actual_completion_date.strftime('%Y-%m-%d %H:%M')
            if record.actual_completion_date else ''
        )
        est_cost = record.estimated_cost if record.estimated_cost is not None else ''
        actual_cost = record.actual_cost if record.actual_cost is not None else ''

        if record.actual_cost is not None:
            total_actual_cost += record.actual_cost

        writer.writerow([
            record.bus.bus_code,
            record.service_date.strftime('%Y-%m-%d'),
            est_duration,
            actual_completion,
            est_cost,
            actual_cost,
        ])

    # Total row
    writer.writerow([])
    writer.writerow(['', '', '', '', 'Total Actual Cost (LKR)', total_actual_cost])

    return response


@_role_required('maintenance', 'full')
def complete_maintenance(request, record_id):
    from django.utils import timezone as tz
    if request.method == 'POST':
        record = get_object_or_404(BusMaintenance, id=record_id)
        record.maintenance_status = 'COMPLETED'
        record.actual_completion_date = tz.now()
        actual_cost = request.POST.get('actual_cost')
        if actual_cost:
            record.actual_cost = actual_cost
        if 'service_bill' in request.FILES:
            record.service_bill = request.FILES['service_bill']
        record.save()
        bus = record.bus
        bus.status = 'AVAILABLE'
        bus.save(update_fields=['status'])
    return redirect(reverse('maintenance_dashboard'))

@_role_required('maintenance', 'view')
def get_bus_mileage(request):
    bus_code = request.GET.get('bus_code', '')
    try:
        bus = Bus.objects.get(bus_code=bus_code)
        return JsonResponse({'mileage': bus.mileage, 'found': True})
    except Bus.DoesNotExist:
        return JsonResponse({'mileage': 0, 'found': False})

@require_POST
@_role_required('maintenance', 'view')
def maintenance_chatbot(request):
    issue = request.POST.get('issue', '')
    recommendation = _maintenance_recommendations(issue)
    return JsonResponse({
        'issue': issue,
        'category': recommendation['category'],
        'recommendations': recommendation['recommendations'],
        'note': 'These are guidance suggestions. Confirm safety-critical repairs with a qualified mechanic.',
    })


@_role_required('scheduling', 'view')
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


@_role_required('maintenance', 'full')
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
        {'form': form, 'module_buttons': _module_buttons(request, 'maintenance')},
    )

@_role_required('current_trips', 'view')
def bus_trip_welcome(request):
    buses = Bus.objects.order_by('bus_code')
    context = {
        'buses': buses,
        'module_buttons': _module_buttons(request, 'current_trips'),
    }
    return render(request, 'core/bus_trip_welcome.html', context)


@_role_required('current_trips', 'view')
def driver_conductor_confirmation(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)
    error_message = ''

    if request.method == 'POST':
        driver_nic = request.POST.get('driver_nic', '').strip()
        conductor_nic = request.POST.get('conductor_nic', '').strip()

        has_valid_assignment = Schedule.objects.filter(
            bus=bus,
            status='SCHEDULED',
            driver__nic_number=driver_nic,
            conductor__c_nic_number=conductor_nic,
        ).exists()

        if has_valid_assignment:
            request.session[f'bus_trip_access_{bus.id}'] = True
            return redirect('current_schedules', bus_id=bus.id)

        error_message = (
            'Access denied. Driver and Conductor NICs do not match a scheduled assignment for this bus.'
        )

    context = {
        'bus': bus,
        'error_message': error_message,
        'module_buttons': _module_buttons(request, 'current_trips'),
    }
    return render(request, 'core/driver_conductor_confirmation.html', context)


@_role_required('current_trips', 'view')
def current_schedules(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)

    if not request.session.get(f'bus_trip_access_{bus.id}'):
        return redirect('driver_conductor_confirmation', bus_id=bus.id)

    schedules = Schedule.objects.select_related(
        'timetable__route', 'driver', 'conductor'
    ).filter(
        bus=bus,
        status='SCHEDULED',
    ).order_by('date', 'timetable__departure_time')

    tank = DepotFuelTank.get_tank()
    refuel_error = request.session.pop('refuel_error', None)
    refuel_success = request.session.pop('refuel_success', None)
    max_bus_capacity = float(bus.fuel_capacity_liters)
    bus_fuel_pct = min(100, (bus.current_fuel_liters / max(max_bus_capacity, 1)) * 100)

    context = {
        'bus': bus,
        'schedules': schedules,
        'module_buttons': _module_buttons(request, 'current_trips'),
        'tank': tank,
        'bus_fuel_pct': round(bus_fuel_pct, 1),
        'max_bus_capacity': max_bus_capacity,
        'refuel_error': refuel_error,
        'refuel_success': refuel_success,
        'low_fuel_warning': bus.current_fuel_liters < 40,
    }
    return render(request, 'core/current_schedules.html', context)

def _combine_schedule_datetime(schedule_date, time_text):
    if not time_text:
        return None
    parsed_time = datetime.strptime(time_text, '%H:%M').time()
    naive_datetime = datetime.combine(schedule_date, parsed_time)
    return timezone.make_aware(naive_datetime, timezone.get_current_timezone())


@_role_required('current_trips', 'full')
def start_trip(request, schedule_id):
    schedule = get_object_or_404(
        Schedule.objects.select_related('bus', 'driver', 'conductor', 'timetable__route'),
        id=schedule_id,
    )

    if not request.session.get(f'bus_trip_access_{schedule.bus.id}'):
        return redirect('driver_conductor_confirmation', bus_id=schedule.bus.id)

    trip, _ = Trip.objects.get_or_create(schedule=schedule)
    error_message = ''

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'start':
            departure_time = request.POST.get('actual_departure_time', '')
            actual_departure_at = _combine_schedule_datetime(schedule.date, departure_time)
            if not actual_departure_at:
                error_message = 'Please select the actual departure time before starting the trip.'
            else:
                trip.start_trip(actual_departure_time=actual_departure_at)
                return redirect('start_trip', schedule_id=schedule.id)

        elif action == 'delay' and trip.t_status in ['ONGOING', 'DELAYED']:
            reason = request.POST.get('delay_reason', '').strip()
            if not reason:
                error_message = 'Please enter a delay reason.'
            else:
                trip.delay_trip(reason=reason)
                return redirect('start_trip', schedule_id=schedule.id)

        elif action == 'end' and trip.t_status in ['ONGOING', 'DELAYED']:
            arrival_time = request.POST.get('actual_arrival_time', '')
            actual_arrival_at = _combine_schedule_datetime(schedule.date, arrival_time)
            if not actual_arrival_at:
                error_message = 'Please select the actual arrival time before ending the trip.'
            else:
                if trip.actual_departure_time and actual_arrival_at < trip.actual_departure_time:
                    actual_arrival_at += timedelta(days=1)
                trip.complete_trip(actual_arrival_time=actual_arrival_at)
                return redirect('current_schedules', bus_id=schedule.bus.id)

    delay_elapsed_seconds = None
    if trip.t_status == 'DELAYED' and trip.delay_started_at:
        delay_elapsed_seconds = int((timezone.now() - trip.delay_started_at).total_seconds())

    # Peak-hour badge
    is_peak = _is_peak(schedule.timetable.departure_time)

    # Auto-run revenue simulation the moment trip becomes ONGOING
    if trip.t_status == 'ONGOING':
        if not TripRevenue.objects.filter(trip=trip).exists():
            _run_simulation(trip)

    context = {
        'schedule': schedule,
        'trip': trip,
        'error_message': error_message,
        'delay_elapsed_seconds': delay_elapsed_seconds,
        'module_buttons': _module_buttons(request, 'current_trips'),
        'is_peak': is_peak,
    }
    return render(request, 'core/start_trip.html', context)


# ── Fuel Dashboard ────────────────────────────────────────
@_role_required('fuel_usage', 'view')
def fuel_dashboard(request):
    import json
    from collections import defaultdict

    tank = DepotFuelTank.get_tank()
    just_refilled = request.session.pop('just_refilled', False)
    fill_pct = tank.percentage()
    fuel_status = 'CRITICAL – LOW FUEL' if tank.is_low() else 'Normal'

    # ── Refuel Log filters ──────────────────────────────────────
    log_date_from  = request.GET.get('log_date_from', '').strip()
    log_date_to    = request.GET.get('log_date_to', '').strip()
    log_bus_code   = request.GET.get('log_bus_code', '').strip()

    # ── Refuel History (chart) filters ─────────────────────────
    hist_date_from = request.GET.get('hist_date_from', '').strip()
    hist_date_to   = request.GET.get('hist_date_to', '').strip()

    # Bus refuel logs for log table
    refuel_logs_qs = BusRefuelLog.objects.select_related('bus').order_by('-refueled_at')
    if log_date_from:
        refuel_logs_qs = refuel_logs_qs.filter(refueled_at__date__gte=log_date_from)
    if log_date_to:
        refuel_logs_qs = refuel_logs_qs.filter(refueled_at__date__lte=log_date_to)
    if log_bus_code:
        refuel_logs_qs = refuel_logs_qs.filter(bus__bus_code__iexact=log_bus_code)
    refuel_logs = refuel_logs_qs[:100]

    # Per-bus summary for chart (with optional date filter)
    history_qs = BusRefuelLog.objects.select_related('bus').order_by('-refueled_at')
    if hist_date_from:
        history_qs = history_qs.filter(refueled_at__date__gte=hist_date_from)
    if hist_date_to:
        history_qs = history_qs.filter(refueled_at__date__lte=hist_date_to)

    # Collect all local bus codes (KS depot) for filtering
    local_bus_codes = set(Bus.objects.values_list('bus_code', flat=True))

    bus_totals = defaultdict(float)
    for log in history_qs:
        code = log.effective_bus_code
        bus_totals[code] += log.amount_liters
    bus_refuel_summary = [
        {
            'bus_code': k,
            'total': round(v, 1),
            'is_external': k not in local_bus_codes,
        }
        for k, v in sorted(bus_totals.items())
    ]

    # All buses (for bus code dropdown)
    all_buses = Bus.objects.all().order_by('bus_code')

    # All buses with low fuel (< 40L) for notifications
    low_fuel_buses = Bus.objects.filter(current_fuel_liters__lt=40).order_by('bus_code')

    # Pass bus data as JSON for the AJAX refuel panel
    bus_fuel_data = list(Bus.objects.values('id', 'bus_code', 'current_fuel_liters', 'fuel_capacity_liters').order_by('bus_code'))

    bus_refuel_added = request.session.pop('bus_refuel_added', False)
    bus_refuel_error = request.session.pop('bus_refuel_error', None)

    context = {
        'tank': tank,
        'fill_pct': fill_pct,
        'fuel_status': fuel_status,
        'just_refilled': just_refilled,
        'module_buttons': _module_buttons(request, 'fuel_usage'),
        'refuel_logs': refuel_logs,
        'bus_refuel_summary_json': json.dumps(bus_refuel_summary),
        'bus_fuel_data_json': json.dumps(bus_fuel_data),
        'low_fuel_buses': low_fuel_buses,
        'all_buses': all_buses,
        'bus_refuel_added': bus_refuel_added,
        'bus_refuel_error': bus_refuel_error,
        # log table filters
        'log_date_from': log_date_from,
        'log_date_to': log_date_to,
        'log_bus_code': log_bus_code,
        # history chart filters
        'hist_date_from': hist_date_from,
        'hist_date_to': hist_date_to,
    }
    return render(request, 'core/fuel_dashboard.html', context)


@_role_required('fuel_usage', 'view')
def fuel_refuel_log_report_csv(request):
    """Generate a CSV report of the Bus Refuel Log, respecting active filters."""
    log_date_from = request.GET.get('log_date_from', '').strip()
    log_date_to   = request.GET.get('log_date_to', '').strip()
    log_bus_code  = request.GET.get('log_bus_code', '').strip()

    qs = BusRefuelLog.objects.select_related('bus').order_by('-refueled_at')
    if log_date_from:
        qs = qs.filter(refueled_at__date__gte=log_date_from)
    if log_date_to:
        qs = qs.filter(refueled_at__date__lte=log_date_to)
    if log_bus_code:
        qs = qs.filter(bus__bus_code__iexact=log_bus_code)

    filename_parts = ['bus_refuel_log']
    if log_bus_code:
        filename_parts.append(f'bus_{log_bus_code}')
    if log_date_from:
        filename_parts.append(f'from_{log_date_from}')
    if log_date_to:
        filename_parts.append(f'to_{log_date_to}')
    filename = '_'.join(filename_parts) + '.csv'

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['SLTB Bus Refuel Log Report'])
    writer.writerow(['Generated on', timezone.now().strftime('%Y-%m-%d %H:%M')])
    date_range = f"{log_date_from or 'All'} to {log_date_to or 'All'}"
    writer.writerow(['Date Range', date_range])
    if log_bus_code:
        writer.writerow(['Bus Filter', log_bus_code])
    writer.writerow([])
    writer.writerow(['Bus Code', 'Amount (L)', 'Fuel Before (L)', 'Fuel After (L)', 'Depot Before (L)', 'Date & Time'])

    total = 0
    for log in qs:
        writer.writerow([
            log.effective_bus_code,
            f'{log.amount_liters:.1f}',
            f'{log.fuel_before:.1f}',
            f'{log.fuel_after:.1f}',
            f'{log.depot_level_before:.0f}',
            log.refueled_at.strftime('%Y-%m-%d %H:%M'),
        ])
        total += log.amount_liters

    writer.writerow([])
    writer.writerow(['Total Fuel Dispensed (L)', f'{total:.1f}'])
    return response


@_role_required('fuel_usage', 'view')
def fuel_refuel_history_report_csv(request):
    """Generate a CSV report of the Refuel History by Bus chart data, respecting active filters."""
    from collections import defaultdict

    hist_date_from = request.GET.get('hist_date_from', '').strip()
    hist_date_to   = request.GET.get('hist_date_to', '').strip()

    qs = BusRefuelLog.objects.select_related('bus').order_by('refueled_at')
    if hist_date_from:
        qs = qs.filter(refueled_at__date__gte=hist_date_from)
    if hist_date_to:
        qs = qs.filter(refueled_at__date__lte=hist_date_to)

    filename_parts = ['refuel_history_by_bus']
    if hist_date_from:
        filename_parts.append(f'from_{hist_date_from}')
    if hist_date_to:
        filename_parts.append(f'to_{hist_date_to}')
    filename = '_'.join(filename_parts) + '.csv'

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['SLTB Refuel History by Bus Report'])
    writer.writerow(['Generated on', timezone.now().strftime('%Y-%m-%d %H:%M')])
    date_range = f"{hist_date_from or 'All'} to {hist_date_to or 'All'}"
    writer.writerow(['Date Range', date_range])
    writer.writerow([])
    writer.writerow(['Bus Code', 'Total Fuel Refilled (L)', 'Number of Refuels'])

    bus_totals = defaultdict(lambda: {'total': 0, 'count': 0})
    for log in qs:
        bus_totals[log.effective_bus_code]['total'] += log.amount_liters
        bus_totals[log.effective_bus_code]['count'] += 1

    grand_total = 0
    for bus_code in sorted(bus_totals.keys()):
        data = bus_totals[bus_code]
        writer.writerow([bus_code, f"{data['total']:.1f}", data['count']])
        grand_total += data['total']

    writer.writerow([])
    writer.writerow(['Grand Total (L)', f'{grand_total:.1f}'])
    return response


@_role_required('fuel_usage', 'full')
def fuel_refill(request):
    if request.method == 'POST':
        tank = DepotFuelTank.get_tank()
        try:
            amount = float(request.POST.get('refill_amount', 0))
        except (ValueError, TypeError):
            amount = 0

        last_date_str = request.POST.get('last_refill_date', '').strip()
        next_date_str = request.POST.get('next_refill_date', '').strip()

        from datetime import date as date_cls
        def parse_date(s):
            try:
                return date_cls.fromisoformat(s) if s else None
            except ValueError:
                return None

        last_date = parse_date(last_date_str)
        next_date = parse_date(next_date_str)

        if amount > 0:
            tank.refill(amount, last_refill_date=last_date, next_refill_date=next_date)
            request.session['just_refilled'] = True

    return redirect('fuel_dashboard')


@_role_required('fuel_usage', 'full')
def bus_refuel(request, bus_id):
    """Refuel a specific bus from the depot tank. Called from current_schedules page."""
    import json
    from django.http import JsonResponse

    bus = get_object_or_404(Bus, id=bus_id)
    tank = DepotFuelTank.get_tank()

    if request.method == 'POST':
        try:
            amount = float(request.POST.get('refuel_amount', 0))
        except (ValueError, TypeError):
            amount = 0

        error = None
        if amount <= 0:
            error = 'Please enter a valid fuel amount.'
        elif amount > tank.current_level_liters:
            error = f'Insufficient depot fuel. Only {tank.current_level_liters:.0f} L available.'
        else:
            max_bus_capacity = float(bus.fuel_capacity_liters)
            space_available = max_bus_capacity - bus.current_fuel_liters
            if amount > space_available:
                error = f'Bus tank can only accept {space_available:.0f} L more (max capacity {max_bus_capacity:.0f} L).'

        if error:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error})
            request.session['refuel_error'] = error
            return redirect('current_schedules', bus_id=bus.id)

        # Perform the refuel
        depot_before = tank.current_level_liters
        bus_before = bus.current_fuel_liters

        # Deduct from depot
        tank.current_level_liters = max(0, tank.current_level_liters - amount)
        tank.save(update_fields=['current_level_liters', 'updated_at'])

        # Add to bus
        bus.current_fuel_liters += amount
        bus.save(update_fields=['current_fuel_liters'])

        # Log the refuel
        BusRefuelLog.objects.create(
            bus=bus,
            amount_liters=amount,
            fuel_before=bus_before,
            fuel_after=bus.current_fuel_liters,
            depot_level_before=depot_before,
            depot_level_after=tank.current_level_liters,
        )

        # Also create a FuelTransaction record
        from .models import FuelTransaction
        FuelTransaction.objects.create(bus=bus, transaction_type='FILL', amount_liters=amount)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'bus_fuel': round(bus.current_fuel_liters, 1),
                'depot_fuel': round(tank.current_level_liters, 1),
                'depot_pct': round(tank.percentage(), 1),
            })

        request.session['refuel_success'] = f'Bus {bus.bus_code} refuelled with {amount:.0f} L.'
        return redirect('current_schedules', bus_id=bus.id)

    return redirect('current_schedules', bus_id=bus.id)


# ── Revenue views ─────────────────────────────────────────────────────────────

@_role_required('revenue', 'view')
def revenue_dashboard(request):
    """Overview dashboard: per-trip revenue cards + summary stats."""
    from django.db.models import Sum, Count, Avg

    trip_revenues = (
        TripRevenue.objects
        .select_related(
            'trip__schedule__bus',
            'trip__schedule__timetable__route',
            'trip__schedule__driver',
            'trip__schedule__conductor',
        )
        .order_by('-created_at')[:200]
    )

    # Split into two aggregate calls to avoid Django's name-collision bug
    # where a field name (e.g. 'total_revenue') clashes with a Sum alias.
    summary_totals = TripRevenue.objects.aggregate(
        total_revenue=Sum('total_revenue'),
        total_passengers=Sum('total_passengers'),
        total_trips=Count('id'),
    )
    summary_avgs = TripRevenue.objects.aggregate(
        avg_revenue=Avg('total_revenue'),
        avg_passengers=Avg('total_passengers'),
    )
    summary = {**summary_totals, **summary_avgs}

    route_breakdown = (
        TripRevenue.objects
        .values(
            'trip__schedule__timetable__route__route_number',
            'trip__schedule__timetable__route__start_location',
            'trip__schedule__timetable__route__end_location',
        )
        .annotate(
            route_revenue=Sum('total_revenue'),
            route_passengers=Sum('total_passengers'),
            trip_count=Count('id'),
        )
        .order_by('-route_revenue')
    )

    bus_breakdown = (
        TripRevenue.objects
        .values(
            'trip__schedule__bus__bus_code',
            'trip__schedule__bus__bus_number',
        )
        .annotate(
            bus_revenue=Sum('total_revenue'),
            bus_passengers=Sum('total_passengers'),
            trip_count=Count('id'),
        )
        .order_by('-bus_revenue')
    )

    context = {
        'trip_revenues': trip_revenues,
        'summary': summary,
        'route_breakdown': list(route_breakdown),
        'bus_breakdown': list(bus_breakdown),
        'module_buttons': _module_buttons(request, 'revenue'),
    }
    return render(request, 'core/revenue_dashboard.html', context)


@_role_required('revenue', 'view')
def trip_revenue_detail(request, trip_id):
    """Per-trip breakdown: stop-by-stop boarding log."""
    trip = get_object_or_404(
        Trip.objects.select_related(
            'schedule__bus',
            'schedule__driver',
            'schedule__conductor',
            'schedule__timetable__route',
        ),
        id=trip_id,
    )

    try:
        trip_revenue = trip.revenue
        boarding_logs = trip_revenue.boarding_logs.all()
    except TripRevenue.DoesNotExist:
        trip_revenue = None
        boarding_logs = []

    context = {
        'trip': trip,
        'trip_revenue': trip_revenue,
        'boarding_logs': boarding_logs,
        'module_buttons': _module_buttons(request, 'revenue'),
    }
    return render(request, 'core/trip_revenue_detail.html', context)


@require_POST
def simulate_trip_revenue_view(request, trip_id):
    """
    AJAX POST – triggered by the trip page JS when the trip goes ONGOING.
    Runs the simulation (idempotent) and returns totals as JSON.
    """
    trip = get_object_or_404(Trip, id=trip_id)
    trip_revenue = _run_simulation(trip)

    return JsonResponse({
        'ok': True,
        'total_passengers': trip_revenue.total_passengers,
        'total_revenue': str(trip_revenue.total_revenue),
    })


@_role_required('revenue', 'view')
def revenue_api_status(request, trip_id):
    """
    GET – polled every 5 s by the trip page while the trip is ONGOING.
    Returns a live (time-interpolated) view of passengers and revenue.
    """
    trip = get_object_or_404(Trip, id=trip_id)

    try:
        tr = trip.revenue
        elapsed_minutes = 0
        if trip.actual_departure_time:
            elapsed = timezone.now() - trip.actual_departure_time
            elapsed_minutes = int(elapsed.total_seconds() / 60)

        route = trip.schedule.timetable.route
        duration_minutes = (
            int(route.estimated_duration.total_seconds() / 60)
            if route.estimated_duration else 60
        )
        duration_minutes = max(1, duration_minutes)

        logs = list(tr.boarding_logs.order_by('stop_order'))
        num_stops = len(logs)

        stops_passed = 0
        if num_stops:
            stops_passed = max(1, int((elapsed_minutes / duration_minutes) * num_stops))
            stops_passed = min(stops_passed, num_stops)
            visible_log = logs[stops_passed - 1]
            live_passengers = visible_log.cumulative_passengers
            live_revenue = float(visible_log.cumulative_revenue)
        else:
            live_passengers = tr.total_passengers
            live_revenue = float(tr.total_revenue)

        return JsonResponse({
            'ok': True,
            'passengers': live_passengers,
            'revenue': live_revenue,
            'total_passengers': tr.total_passengers,
            'total_revenue': float(tr.total_revenue),
            'stops_passed': stops_passed,
            'num_stops': num_stops,
        })

    except TripRevenue.DoesNotExist:
        return JsonResponse({'ok': False, 'passengers': 0, 'revenue': 0.0})


@_role_required('fuel_usage', 'full')
def fuel_bus_refuel(request):
    """AJAX endpoint: refuel a bus (or external bus) from the fuel dashboard."""
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    tank = DepotFuelTank.get_tank()
    is_external = request.POST.get('is_external', 'false').lower() == 'true'
    amount_str = request.POST.get('amount', '0').strip()

    try:
        amount = float(amount_str)
    except (ValueError, TypeError):
        amount = 0

    if amount <= 0:
        return JsonResponse({'success': False, 'error': 'Please enter a valid fuel amount greater than zero.'})
    if amount > tank.current_level_liters:
        return JsonResponse({'success': False, 'error': f'Insufficient depot fuel. Only {tank.current_level_liters:.0f} L available.'})

    depot_before = tank.current_level_liters

    if is_external:
        ext_code = request.POST.get('external_bus_code', '').strip().upper()
        if not ext_code:
            return JsonResponse({'success': False, 'error': 'Please enter the external bus code.'})
        tank.current_level_liters = max(0, tank.current_level_liters - amount)
        tank.save(update_fields=['current_level_liters', 'updated_at'])
        BusRefuelLog.objects.create(
            bus=None,
            external_bus_code=ext_code,
            is_external_bus=True,
            amount_liters=amount,
            fuel_before=0,
            fuel_after=0,
            depot_level_before=depot_before,
            depot_level_after=tank.current_level_liters,
        )
        return JsonResponse({
            'success': True,
            'message': f'External bus {ext_code} refuelled with {amount:.0f} L.',
            'depot_fuel': round(tank.current_level_liters, 1),
            'depot_pct': round(tank.percentage(), 1),
            'bus_code': ext_code,
            'bus_fuel_after': None,
            'is_external': True,
        })
    else:
        bus_id = request.POST.get('bus_id', '').strip()
        try:
            bus = Bus.objects.get(id=int(bus_id))
        except (Bus.DoesNotExist, ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Bus not found.'})

        max_cap = float(bus.fuel_capacity_liters)
        space = max_cap - bus.current_fuel_liters
        if amount > space:
            return JsonResponse({'success': False, 'error': f'Bus tank can only accept {space:.0f} L more (capacity: {max_cap:.0f} L).'})

        bus_before = bus.current_fuel_liters
        tank.current_level_liters = max(0, tank.current_level_liters - amount)
        tank.save(update_fields=['current_level_liters', 'updated_at'])
        bus.current_fuel_liters = min(max_cap, bus.current_fuel_liters + amount)
        bus.save(update_fields=['current_fuel_liters'])
        BusRefuelLog.objects.create(
            bus=bus,
            is_external_bus=False,
            amount_liters=amount,
            fuel_before=bus_before,
            fuel_after=bus.current_fuel_liters,
            depot_level_before=depot_before,
            depot_level_after=tank.current_level_liters,
        )
        from .models import FuelTransaction
        FuelTransaction.objects.create(bus=bus, transaction_type='FILL', amount_liters=amount)
        bus_pct = round((bus.current_fuel_liters / max(max_cap, 1)) * 100, 1)
        return JsonResponse({
            'success': True,
            'message': f'Bus {bus.bus_code} refuelled with {amount:.0f} L.',
            'depot_fuel': round(tank.current_level_liters, 1),
            'depot_pct': round(tank.percentage(), 1),
            'bus_code': bus.bus_code,
            'bus_fuel_after': round(bus.current_fuel_liters, 1),
            'bus_fuel_pct': bus_pct,
            'bus_capacity': int(max_cap),
            'is_external': False,
        })


# ── Attendance / Clock-in Clock-out module ────────────────────────────────────

def opening_view(request):
    """Splash/opening page — no login required."""
    return render(request, 'core/opening.html')


def clock_role_select(request):
    """Page to choose Driver or Conductor before clocking in/out."""
    action = request.GET.get('action', 'in')
    if action not in ('in', 'out'):
        action = 'in'
    return render(request, 'core/clock_role_select.html', {
        'action': action,
        'action_label': 'clocking in' if action == 'in' else 'clocking out',
        'page_title': 'Clock In' if action == 'in' else 'Clock Out',
    })


def clock_action(request):
    """Shows analog clock + NIC input. Handles POST to perform clock-in/out."""
    action = request.GET.get('action') or request.POST.get('action', 'in')
    role   = request.GET.get('role')   or request.POST.get('role', 'driver')

    if action not in ('in', 'out'):
        action = 'in'
    if role not in ('driver', 'conductor'):
        role = 'driver'

    role_label = 'Driver' if role == 'driver' else 'Conductor'
    action_label = 'Clock-In' if action == 'in' else 'Clock-Out'

    ctx = {
        'action': action,
        'role': role,
        'role_label': role_label,
        'page_title': f'{action_label} as {role_label}',
        'message': None,
        'success': False,
    }

    if request.method == 'POST':
        nic = request.POST.get('nic', '').strip().upper()
        message, success = _perform_clock_action(nic, role, action)
        if success:
            return redirect('opening')
        ctx['message'] = message
        ctx['success'] = False

    return render(request, 'core/clock_action.html', ctx)


def _perform_clock_action(nic, role, action):
    """Core logic: validate NIC, update attendance & status. Returns (message, success)."""
    if role == 'driver':
        try:
            employee = Driver.objects.get(nic_number__iexact=nic)
        except Driver.DoesNotExist:
            return ('Driver not found. Please check your NIC number.', False)

        attendance, _ = StaffAttendance.objects.get_or_create(
            driver=employee,
            defaults={'status': 'OFF_DUTY'}
        )
    else:
        try:
            employee = Conductor.objects.get(c_nic_number__iexact=nic)
        except Conductor.DoesNotExist:
            return ('Conductor not found. Please check your NIC number.', False)

        attendance, _ = StaffAttendance.objects.get_or_create(
            conductor=employee,
            defaults={'status': 'OFF_DUTY'}
        )

    name = attendance.staff_name

    if action == 'in':
        attendance.mark_available()
        return (f'Welcome, {name}! Your shift has started successfully. Status: Available.', True)
    else:
        if attendance.status == 'OFF_DUTY' and attendance.clock_in_time is None:
            return (f'{role.capitalize()} has not clocked in yet today.', False)
        attendance.mark_off_duty()
        return (f'Goodbye, {name}! Your shift has ended. Status: Off Duty.', True)


def clock_lookup_api(request):
    """AJAX endpoint: lookup employee by NIC and return name/status."""
    nic    = request.GET.get('nic', '').strip().upper()
    role   = request.GET.get('role', 'driver')
    action = request.GET.get('action', 'in')

    if len(nic) < 9:
        return JsonResponse({'found': False, 'message': 'NIC too short'})

    if role == 'driver':
        try:
            emp = Driver.objects.get(nic_number__iexact=nic)
        except Driver.DoesNotExist:
            return JsonResponse({'found': False, 'message': 'Driver not found'})
        attendance = StaffAttendance.objects.filter(driver=emp).first()
        status = emp.get_driver_status_display()
        already_in  = attendance and attendance.status == 'AVAILABLE'
        already_out = attendance and attendance.status == 'OFF_DUTY' and attendance.clock_out_time is not None
        return JsonResponse({
            'found': True,
            'name': emp.driver_name,
            'role': 'Driver',
            'status': status,
            'already_clocked_in': already_in,
            'already_clocked_out': already_out,
        })
    else:
        try:
            emp = Conductor.objects.get(c_nic_number__iexact=nic)
        except Conductor.DoesNotExist:
            return JsonResponse({'found': False, 'message': 'Conductor not found'})
        attendance = StaffAttendance.objects.filter(conductor=emp).first()
        status = emp.get_conductor_status_display()
        already_in  = attendance and attendance.status == 'AVAILABLE'
        already_out = attendance and attendance.status == 'OFF_DUTY' and attendance.clock_out_time is not None
        return JsonResponse({
            'found': True,
            'name': emp.conductor_name,
            'role': 'Conductor',
            'status': status,
            'already_clocked_in': already_in,
            'already_clocked_out': already_out,
        })


@_role_required('admin_attendance', 'view')
def attendance_dashboard(request):
    """Admin view: all attendance records."""
    from django.db.models import Q

    filter_role   = request.GET.get('role', '')
    filter_status = request.GET.get('status', '')
    filter_date   = request.GET.get('date', '')

    qs = StaffAttendance.objects.select_related('driver', 'conductor').order_by('-updated_at')

    if filter_role == 'driver':
        qs = qs.filter(driver__isnull=False)
    elif filter_role == 'conductor':
        qs = qs.filter(conductor__isnull=False)

    if filter_status in ('AVAILABLE', 'OFF_DUTY'):
        qs = qs.filter(status=filter_status)

    if filter_date:
        from datetime import date as date_cls
        try:
            d = date_cls.fromisoformat(filter_date)
            qs = qs.filter(clock_in_time__date=d)
        except ValueError:
            pass

    total       = qs.count()
    available   = qs.filter(status='AVAILABLE').count()
    off_duty    = qs.filter(status='OFF_DUTY').count()
    drivers_in  = qs.filter(driver__isnull=False, status='AVAILABLE').count()
    conds_in    = qs.filter(conductor__isnull=False, status='AVAILABLE').count()

    ctx = {
        'attendance_records': qs,
        'total': total,
        'available': available,
        'off_duty': off_duty,
        'drivers_in': drivers_in,
        'conductors_in': conds_in,
        'filter_role': filter_role,
        'filter_status': filter_status,
        'filter_date': filter_date,
        'module_buttons': _module_buttons(request, 'attendance'),
    }
    return render(request, 'core/attendance_dashboard.html', ctx)


# ── Route Map Data API ────────────────────────────────────────────────────────
@_role_required('manage_routes', 'view')
def route_map_data(request, route_id):
    """
    Returns JSON with ordered stops (name, lat, lng) for the given route.
    Used by the Leaflet / OSRM map on the Route Management dashboard.
    """
    route = get_object_or_404(Route, id=route_id)
    route_stops = (
        RouteStop.objects.select_related('stop')
        .filter(route=route)
        .order_by('order')
    )
    stops = [
        {
            'name'  : rs.stop.stop_name,
            'lat'   : rs.stop.latitude,
            'lng'   : rs.stop.longitude,
            'order' : rs.order,
        }
        for rs in route_stops
    ]
    return JsonResponse({'route_id': route_id, 'stops': stops})
