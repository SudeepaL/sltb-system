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
        default='OFF_DUTY'
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
    current_fuel_liters = models.FloatField(default=0)
    fuel_efficiency_km_per_liter = models.FloatField(default=4.0)
    image = models.ImageField(upload_to='bus_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    #Linking driver to bus:
    #driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.bus_code} ({self.bus_number})"
    
    @classmethod
    def refuel_by_bus_code(cls, bus_code, filled_liters):
        bus = cls.objects.get(bus_code=bus_code)
        bus.add_fuel(filled_liters)
        return bus

    def add_fuel(self, filled_liters):
        if filled_liters <= 0:
            raise ValueError("Fuel amount must be greater than zero.")
        self.current_fuel_liters += filled_liters
        self.save(update_fields=['current_fuel_liters'])
        FuelTransaction.objects.create(
            bus=self,
            transaction_type='FILL',
            amount_liters=filled_liters
        )

    def burn_fuel_for_distance(self, distance_km):
        if not distance_km or distance_km <= 0:
            return 0

        burned_liters = distance_km / self.fuel_efficiency_km_per_liter
        self.current_fuel_liters = max(0, self.current_fuel_liters - burned_liters)
        self.save(update_fields=['current_fuel_liters'])
        FuelTransaction.objects.create(
            bus=self,
            transaction_type='BURN',
            amount_liters=burned_liters
        )
        return burned_liters
       
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
        self.schedule.bus.burn_fuel_for_distance(self.schedule.timetable.route.distance)

        #Only available if there is no return trip: 
        if not self.return_trip:
            self.schedule.driver.driver_status = 'AVAILABLE'
            self.schedule.driver.save()

            self.schedule.conductor.conductor_status = 'AVAILABLE'
            self.schedule.conductor.save()

        self.save()

    def __str__(self):
        return f"{self.schedule} - {self.t_status}"
    
#Fule module: 
class FuelTransaction(models.Model):
    TRANSACTION_CHOICES = [
        ('FILL', 'Filled'),
        ('BURN', 'Burned'),
    ]

    bus = models.ForeignKey('Bus', on_delete=models.CASCADE, related_name='fuel_transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_CHOICES)
    amount_liters = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.bus.bus_code} - {self.transaction_type} - {self.amount_liters:.2f}L"
    
#Attendence module 
class StaffAttendance(models.Model):
    ATTENDANCE_STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('OFF_DUTY', 'Off Duty'),
    ]

    driver = models.OneToOneField('Driver', on_delete=models.CASCADE, null=True, blank=True)
    conductor = models.OneToOneField('Conductor', on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS_CHOICES, default='OFF_DUTY')
    clock_in_time = models.DateTimeField(null=True, blank=True)
    clock_out_time = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    (models.Q(driver__isnull=False) & models.Q(conductor__isnull=True))
                    | (models.Q(driver__isnull=True) & models.Q(conductor__isnull=False))
                ),
                name='attendance_has_exactly_one_staff_member',
            ),
        ]

    @property
    def staff_name(self):
        return self.driver.driver_name if self.driver else self.conductor.conductor_name

    @property
    def staff_type(self):
        return 'Driver' if self.driver else 'Conductor'

    def mark_available(self):
        now = timezone.now()
        self.status = 'AVAILABLE'
        self.clock_in_time = now
        self.clock_out_time = None
        if self.driver:
            self.driver.driver_status = 'AVAILABLE'
            self.driver.save(update_fields=['driver_status'])
        if self.conductor:
            self.conductor.conductor_status = 'AVAILABLE'
            self.conductor.save(update_fields=['conductor_status'])
        self.save(update_fields=['status', 'clock_in_time', 'clock_out_time', 'updated_at'])

    def mark_off_duty(self):
        now = timezone.now()
        self.status = 'OFF_DUTY'
        self.clock_out_time = now
        if self.driver:
            self.driver.driver_status = 'OFF_DUTY'
            self.driver.save(update_fields=['driver_status'])
        if self.conductor:
            self.conductor.conductor_status = 'OFF_DUTY'
            self.conductor.save(update_fields=['conductor_status'])
        self.save(update_fields=['status', 'clock_out_time', 'updated_at'])

    def __str__(self):
        return f"{self.staff_type}: {self.staff_name} ({self.status})"
    
#Bus maintenance module
class BusMaintenance(models.Model):
    bus = models.ForeignKey('Bus', on_delete=models.CASCADE, related_name='maintenance_records')
    service_date = models.DateField(default=timezone.now)
    mileage = models.PositiveIntegerField(help_text='Current mileage at the time of service')
    service_history = models.TextField(help_text='Summary of service history / issue reported')
    maintenance_details = models.TextField(help_text='Maintenance work completed for this service')
    next_service_due_mileage = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-service_date', '-created_at']

    def __str__(self):
        return f"{self.bus.bus_code} maintenance on {self.service_date}"




