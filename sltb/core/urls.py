from django.urls import path

from . import views

urlpatterns = [
    path('', views.bus_dashboard, name='bus_dashboard'),
    path('drivers/', views.driver_dashboard, name='driver_dashboard'),
    path('conductors/', views.conductor_dashboard, name='conductor_dashboard'),
    path('routes/', views.route_dashboard, name='route_dashboard'),
    path('routes/add/', views.add_route, name='add_route'),
    path('routes/<int:route_id>/stops/', views.manage_route_stops, name='manage_route_stops'),
    path('routes/<int:route_id>/stops/add/', views.add_stop, name='add_stop'),
    path('buses/add/', views.add_bus, name='add_bus'),
    path('buses/<int:bus_id>/manage/', views.manage_bus, name='manage_bus'),

    path('drivers/add/', views.add_driver, name='add_driver'),
    path('drivers/<int:driver_id>/manage/', views.manage_driver, name='manage_driver'),
    path('conductors/add/', views.add_conductor, name='add_conductor'),
    path('conductors/<int:conductor_id>/manage/', views.manage_conductor, name='manage_conductor'),
    path('timetables/', views.timetable_dashboard, name='timetable_dashboard'),
    path('timetables/add/', views.add_timetable, name='add_timetable'),
    path('scheduling/', views.scheduling_dashboard, name='scheduling_dashboard'),
    path('scheduling/add/', views.add_schedule, name='add_schedule'),
    path('scheduling/outbound-for-return/', views.get_outbound_for_return, name='get_outbound_for_return'),
    path('scheduling/resource-data/', views.get_schedule_resource_data, name='get_schedule_resource_data'),
    path('maintenance/', views.maintenance_dashboard, name='maintenance_dashboard'),
    path('maintenance/add/', views.add_maintenance, name='add_maintenance'),
    path('maintenance/bus-mileage/', views.get_bus_mileage, name='get_bus_mileage'),
    path('maintenance/chatbot/', views.maintenance_chatbot, name='maintenance_chatbot'),
    path('maintenance/complete/<int:record_id>/', views.complete_maintenance, name='complete_maintenance'),
    path('maintenance/report/csv/', views.maintenance_report_csv, name='maintenance_report_csv'),
    path('trips/', views.bus_trip_welcome, name='bus_trip_welcome'),
    path('trips/bus/<int:bus_id>/confirmation/', views.driver_conductor_confirmation, name='driver_conductor_confirmation'),
    path('trips/bus/<int:bus_id>/current-schedules/', views.current_schedules, name='current_schedules'),
    path('trips/start/<int:schedule_id>/', views.start_trip, name='start_trip'),
    path('fuel/', views.fuel_dashboard, name='fuel_dashboard'),
    path('fuel/refill/', views.fuel_refill, name='fuel_refill'),
    path('fuel/bus/<int:bus_id>/refuel/', views.bus_refuel, name='bus_refuel'),

    # ── Revenue module ────────────────────────────────────────────────────────
    path('revenue/', views.revenue_dashboard, name='revenue_dashboard'),
    path('revenue/trip/<int:trip_id>/', views.trip_revenue_detail, name='trip_revenue_detail'),
    path('revenue/trip/<int:trip_id>/simulate/', views.simulate_trip_revenue_view, name='simulate_trip_revenue'),
    path('revenue/trip/<int:trip_id>/status/', views.revenue_api_status, name='revenue_api_status'),
]
