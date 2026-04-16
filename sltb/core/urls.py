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
    path('maintenance/', views.maintenance_dashboard, name='maintenance_dashboard'),
    path('maintenance/add/', views.add_maintenance, name='add_maintenance'),
    path('maintenance/bus-mileage/', views.get_bus_mileage, name='get_bus_mileage'),
]