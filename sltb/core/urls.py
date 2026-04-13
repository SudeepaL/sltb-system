from django.urls import path
from . import views

urlpatterns = [
    path('', views.bus_dashboard, name='bus_dashboard'),
    path('buses/<int:bus_id>/manage/', views.manage_bus, name='manage_bus'),
]