from django.db import models

class Bus(models.Model):
    BUS_TYPE_CHOICES = [
        ('AC' , 'AC'),
        ('NON_AC' , 'Non-AC'),
    ]

    STATUS_CHOICES = [
        ('AVAILABLE' , 'Available'),
        ('MAINTENANCE' , 'Maintenance'),
        ('ON_ROUTE' , 'On Route'),
    ]

    bus_number = models.CharField(max_length=20, unique=True)
    bus_code = models.CharField(max_length=10, unique=True)
    model = models.CharField(max_length=50, blank=True, null=True)
    capacity = models.PositiveBigIntegerField()
    bus_type = models.CharField(max_length=10, choices=BUS_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    depot = models.CharField(max_length=50)
    image = models.ImageField(upload_to='bus_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bus_code} ({self.bus_number})"
    
class Driver(models.Model):
    DRIVER_STATUS_CHOICES = [
        ('AVAIALABLE' , 'Available'),
        ('ON_ROUTE' , 'On Route'),
        ('OFF_DUTY' , 'Off Duty'),
    ]    

    GENDER_CHOICES = [
        ('MALE' , 'Male'),
        ('FEMALE' , 'Female'),
    ]

    driver_name = models.CharField(max_length=100)
    dob = models.DateField()
    nic_number = models.CharField(max_length=20, unique=True)
    driving_license_number = models.CharField(max_length=50, unique=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    phone_number = models.CharField(max_length=10)
    email = models.EmailField(blank=True, null=True)
    driver_address = models.TextField(blank=True, null=True)
    driver_status = models.CharField(
        max_length=20,
        choices=DRIVER_STATUS_CHOICES,
        default='AVAILABLE'
    )
    driver_registration_date = models.DateField()
    driver_id_image = models.ImageField(
        upload_to='driver_ids/',
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.driver_name} ({self.driving_license_number})"



