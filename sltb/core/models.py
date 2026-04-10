from django.db import models
from django.utils import timezone

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
    
#Timetable class
class TimeTable(models.Model):
    route = models.ForeignKey('Route', on_delete=models.CASCADE)
    departure_time = models.TimeField()
    arrival_time = models.TimeField()

    DAY_CHOICES = [
        ('daily', 'Daily'),
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]

    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES, default='daily')

    DIRECTION_CHOICES = [
        ('OUTBOUND', 'Outbound'),
        ('RETURN', 'Return'),
    ]

    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)

    def __str__(self):
        return f"{self.route} - {self.departure_time} ({self.direction})"
    
#Schedule class:
class Schedule(models.Model):
    timetable = models.ForeignKey('TimeTable', on_delete=models.CASCADE)
    bus = models.ForeignKey('Bus', on_delete=models.CASCADE)
    driver = models.ForeignKey('Driver', on_delete=models.CASCADE, null=True, blank=True)
    conductor = models.ForeignKey('Conductor', on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()

    S_STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'), 
    ]
    
    status = models.CharField(max_length=20, choices=S_STATUS_CHOICES, default='SCHEDULED')

    def __str__(self):
        return f"{self.timetable} - {self.date}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        #auto assgning same driver conductor for return trips 
        if self.timetable.direction == 'RETURN':
            outbound = Schedule.objects.filter(
                timetable__route=self.timetable.route,
                timetable__direction='OUTBOUND',
                date=self.date
            ).first()

            if outbound:
                self.driver = outbound.driver
                self.conductor = outbound.conductor
                super().save(update_fields=['driver' , 'conductor'])
    
#Trip class: 
class Trip(models.Model):
    schedule = models.OneToOneField('Schedule', on_delete=models.CASCADE)
    return_trip = models.OneToOneField(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='outbound_trip'
    )
    
    T_STATUS_CHOICES = [
        ('NOT_STARTED', 'Not Started'),
        ('ONGOING', 'Ongoing'),
        ('DELAYED', 'Delayed'),
        ('COMPLETED', 'Completed'),
    ]

    t_status = models.CharField(max_length=20, choices=T_STATUS_CHOICES, default='NOT_STARTED')
    actual_departure_time = models.DateTimeField(null=True, blank=True)
    actual_arrival_time = models.DateTimeField(null=True, blank=True)
    delay_reason = models.TextField(null=True, blank=True)

    def start_trip(self):
        self.t_status = 'ONGOING'
        self.actual_departure_time = timezone.now()

        #If driver or conductor busy:
        self.schedule.driver.driver_status = 'ON_ROUTE'
        self.schedule.driver.save()
        self.schedule.conductor.conductor_status = 'ON_DUTY'
        self.schedule.conductor.save()

        self.save()

    def delay_trip(self, reason):
        self.t_status = 'DELAYED'
        self.delay_reason = reason
        self.save()

    def complete_trip(self):
        self.t_status = 'COMPLETED'
        self.actual_arrival_time = timezone.now()

        #Only available if there is no return trip: 
        if not self.return_trip:
            self.schedule.driver.driver_status = 'AVAILABLE'
            self.schedule.driver.save()

            self.schedule.conductor.conductor_status = 'AVAILABLE'
            self.schedule.conductor.save()

        self.save()

    def __str__(self):
        return f"{self.schedule} - {self.t_status}"




