from django.db import models

#Driver model:
class Driver(models.Model):
    DRIVER_STATUS_CHOICES = [
        ('AVAILABLE' , 'Available'),
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
    
#Conductor model:
class Conductor(models.Model):
    CONDUCTOR_STATUS_CHOICES = [
        ('AVAILABLE' , 'Available'),
        ('ON_DUTY' , 'On Duty'),
        ('OFF_DUTY' , 'Off Duty'),
    ]    

    GENDER_CHOICES = [
        ('MALE' , 'Male'),
        ('FEMALE' , 'Female'),
    ]

    conductor_name = models.CharField(max_length=100)
    c_dob = models.DateField()
    c_nic_number = models.CharField(max_length=20, unique=True)
    c_gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    c_phone_number = models.CharField(max_length=10)
    c_email = models.EmailField(blank=True, null=True)
    conductor_address = models.TextField(blank=True, null=True)
    conductor_status = models.CharField(
        max_length=20,
        choices=CONDUCTOR_STATUS_CHOICES,
        default='AVAILABLE'
    )
    conductor_registration_date = models.DateField()
    conductor_id_image = models.ImageField(
        upload_to='driver_ids/',
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.conductor_name
    
#Bus Model: 
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

    #Linking driver to bus:
    #driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.bus_code} ({self.bus_number})"
    
#Route class:
class Route(models.Model):
    route_number = models.CharField(max_length=10)
    start_location = models.CharField(max_length=100)
    end_location = models.CharField(max_length=100)
    distance = models.FloatField(null=True, blank=True)
    estimated_duration = models.DurationField()

    def __str__(self):
        return self.route_number
        
#Stop class: 
class Stop(models.Model):
    #route = models.ForeignKey(Route, on_delete=models.CASCADE)
    stop_name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    #order = models.PositiveBigIntegerField()

    def __str__(self):
        return self.stop_name

#Route stop class (since one stop has many route numbers)
class RouteStop(models.Model):
    route = models.ForeignKey('Route', on_delete=models.CASCADE)
    stop = models.ForeignKey('Stop', on_delete=models.CASCADE)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.route.route_number} - {self.stop.stop_name}"

#Schedule class:
class Schedule(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    bus = models.ForeignKey('Bus', on_delete=models.CASCADE)
    driver = models.ForeignKey('Driver', on_delete=models.CASCADE)
    depature_time = models.TimeField()
    arrival_time = models.TimeField()
    date = models.DateField()

    def __str__(self):
        return f"{self.route.route_number} - {self.date}"




