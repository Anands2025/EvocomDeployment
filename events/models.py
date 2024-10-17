from django.utils import timezone
from django.db import models
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db.models import Case, When, Value, CharField
from communities.models import Community
from users.models import User
from django.core.exceptions import ValidationError

class EventManager(models.Manager):
    def with_status(self):
        now = timezone.now()
        return self.annotate(
            current_status=Case(
                When(start_datetime__lte=now, end_datetime__gt=now, then=Value('ongoing')),
                When(end_datetime__lte=now, then=Value('completed')),
                default=Value('upcoming'),
                output_field=CharField(),
            )
        )

class EventCategory(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    status=models.CharField(max_length=255,default='enabled')

    def __str__(self):
        return self.name
class EventSubCategory(models.Model):
    event_category = models.ForeignKey(EventCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return f"{self.name} ({self.event_category.name})"
class Event(models.Model):
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(EventCategory, on_delete=models.CASCADE)
    cover_image = models.ImageField(upload_to='event_covers/', null=True, blank=True)  # New field for cover image
    start_datetime = models.DateTimeField()  # New field for start date and time
    end_datetime = models.DateTimeField()    # New field for end date and time
    address = models.CharField(max_length=255)
    location = models.TextField()
    location_description = models.TextField(null=True, blank=True)  # New field for location description
    registration_fee=models.DecimalField(blank=True,null=True,decimal_places=2,max_digits=10)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='upcoming')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    reminder_sent = models.BooleanField(default=False)
    last_reminder_sent = models.DateTimeField(null=True, blank=True)
    volunteer_tasks = models.TextField(blank=True, null=True, help_text="List of tasks for volunteers")

    def __str__(self):
        return self.name

    def set_lat_long(self):
        geolocator = Nominatim(user_agent="evocom")
        try:
            location = geolocator.geocode(self.address)
            if location:
                self.latitude = location.latitude
                self.longitude = location.longitude
                self.save()
        except (GeocoderTimedOut, GeocoderServiceError):
            print(f"Geocoding failed for address: {self.address}")

    @property
    def current_status(self):
        now = timezone.now()
        if self.start_datetime <= now < self.end_datetime:
            return 'ongoing'
        elif now >= self.end_datetime:
            return 'completed'
        else:
            return 'upcoming'

    def update_success_metrics(self, actual_attendees):
        # Calculate max_attendees as the total number of registrations
        max_attendees = self.eventregistration_set.count()
        
        # Avoid division by zero
        attendance_ratio = actual_attendees / max_attendees if max_attendees > 0 else 0

        if hasattr(self, 'success_metrics'):
            self.success_metrics.attendance_ratio = attendance_ratio
            self.success_metrics.save()
        else:
            EventSuccessMetrics.objects.create(
                event=self,
                attendance_ratio=attendance_ratio,
                event_category=self.category.name,
                community_category=self.community.category.name,
                community_name=self.community.name,
                start_time=self.start_datetime.time(),
                end_time=self.end_datetime.time(),
                duration_hours=(self.end_datetime - self.start_datetime).total_seconds() / 3600,
                is_weekend=self.start_datetime.weekday() >= 5,
                is_free=self.registration_fee == 0,
                keywords=EventSuccessMetrics.extract_keywords(self.description)
            )

    def get_total_registrations(self):
        return self.eventregistration_set.count()

    def get_actual_attendees(self):
        return self.eventregistration_set.filter(attended=True).count()

    def should_send_reminder(self):
        if not self.last_reminder_sent:
            return True
        return (self.start_datetime - timezone.now()).days <= 1 and \
               (timezone.now() - self.last_reminder_sent).days >= 1

@receiver(pre_save, sender=Event)
def update_event_status(sender, instance, **kwargs):
    instance.status = instance.current_status

@receiver(post_save, sender=Event)
def create_event_success_metrics(sender, instance, created, **kwargs):
    if created:
        EventSuccessMetrics.objects.create(
            event=instance,
            attendance_ratio=0,  # Initial value, to be updated later
            event_category=instance.category.name,
            community_category=instance.community.category.name,
            community_name=instance.community.name,
            start_time=instance.start_datetime.time(),
            end_time=instance.end_datetime.time(),
            duration_hours=(instance.end_datetime - instance.start_datetime).total_seconds() / 3600,
            is_weekend=instance.start_datetime.weekday() >= 5,
            is_free=instance.registration_fee == 0,
            keywords=EventSuccessMetrics.extract_keywords(instance.description)
        )

class Task(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(EventCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name
class EventRegistration(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('canceled', 'Canceled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    registration_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    attended = models.BooleanField(default=False)  # New field for attendance

    def __str__(self):
        return f"{self.user.username} - {self.event.name}"

    def save(self, *args, **kwargs):
        if VolunteerRegistration.objects.filter(user=self.user, event=self.event).exists():
            raise ValidationError("Volunteers cannot register as participants for the same event.")
        super().save(*args, **kwargs)

class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    event_registration = models.OneToOneField(EventRegistration, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50)
    order_id = models.CharField(max_length=100, unique=True)  # New field for Razorpay order ID
    payment_id = models.CharField(max_length=100, unique=True, null=True, blank=True)  # Renamed from transaction_id
    status = models.CharField(max_length=15, choices=PAYMENT_STATUS_CHOICES, default='pending')
    invoice_file = models.FileField(upload_to='payment_invoices/', null=True, blank=True)  # New field for invoice file

    def __str__(self):
        return f"Payment for {self.event_registration} - {self.amount}"

class EventSuccessMetrics(models.Model):
    event = models.OneToOneField('Event', on_delete=models.SET_NULL, null=True, blank=True, related_name='success_metrics')
    attendance_ratio = models.FloatField()
    event_category = models.CharField(max_length=255)
    community_category = models.CharField(max_length=255)
    community_name = models.CharField(max_length=255)
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_hours = models.FloatField(default=0)
    is_weekend = models.BooleanField()
    is_free = models.BooleanField()
    keywords = models.TextField()  # Store as comma-separated values
    is_synthetic = models.BooleanField(default=False)

    def __str__(self):
        return f"Metrics for {self.event.name if self.event else 'Deleted Event'}"

    def save(self, *args, **kwargs):
        if not self.pk:  # Only calculate these fields when first creating the object
            event = self.event
            self.start_time = event.start_datetime.time()
            self.end_time = event.end_datetime.time()
            self.duration_hours = (event.end_datetime - event.start_datetime).total_seconds() / 3600
            self.is_weekend = event.start_datetime.weekday() >= 5
            self.is_free = event.registration_fee == 0
            self.keywords = self.extract_keywords(event.description)
        super().save(*args, **kwargs)

    @staticmethod
    def extract_keywords(description):
        # This is a simple keyword extraction. You might want to use a more sophisticated method.
        common_words = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'])
        words = description.lower().split()
        keywords = [word for word in words if word not in common_words and len(word) > 3]
        return ','.join(set(keywords[:10]))  # Return up to 10 unique keywords

class VolunteerRegistration(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    registration_date = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    assigned_task = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('user', 'event')

    def __str__(self):
        return f"{self.user.username} - {self.event.name} (Volunteer)"
