from django.urls import path

from . import views

urlpatterns = [
    path('', views.bus_dashboard, name='bus_dashboard'),
    path('drivers/', views.driver_dashboard, name='driver_dashboard'),
    path('conductors/', views.conductor_dashboard, name='conductor_dashboard'),
    path('buses/add/', views.add_bus, name='add_bus'),
    path('buses/<int:bus_id>/manage/', views.manage_bus, name='manage_bus'),

    path('drivers/add/', views.add_driver, name='add_driver'),
    path('drivers/<int:driver_id>/manage/', views.manage_driver, name='manage_driver'),
    path('conductors/add/', views.add_conductor, name='add_conductor'),
    path('conductors/<int:conductor_id>/manage/', views.manage_conductor, name='manage_conductor'),
]