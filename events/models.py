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
import secrets
import decimal
from django.core.validators import MinValueValidator
from django.core.files import File
import qrcode
from io import BytesIO
import uuid

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
    youtube_stream_url = models.URLField(max_length=255, blank=True, null=True)
    is_streaming = models.BooleanField(default=False)
    max_attendees = models.PositiveIntegerField(
        default=50,
        help_text="Maximum number of attendees allowed for this event"
    )
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    dynamic_pricing_enabled = models.BooleanField(default=False)
    price_increment_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=10.00,
        help_text="Percentage to increase/decrease price based on demand"
    )

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

    def generate_stream_key(self):
        if not self.stream_key:
            self.stream_key = secrets.token_urlsafe(16)
            self.save()
        return self.stream_key

    def calculate_dynamic_price(self):
        if not self.dynamic_pricing_enabled:
            return self.base_price

        # Get total registrations
        total_registrations = self.eventregistration_set.count()
        capacity_percentage = (total_registrations / self.max_attendees) * 100

        # Get registration trend (registrations in last 24 hours)
        recent_registrations = self.eventregistration_set.filter(
            registration_date__gte=timezone.now() - timezone.timedelta(hours=24)
        ).count()

        # Base price adjustment based on capacity filled
        if capacity_percentage >= 80:
            adjustment = decimal.Decimal(self.price_increment_percentage * 2)  # High demand
        elif capacity_percentage >= 50:
            adjustment = decimal.Decimal(self.price_increment_percentage)  # Medium demand
        elif capacity_percentage <= 20:
            adjustment = decimal.Decimal(-self.price_increment_percentage)  # Low demand
        else:
            adjustment = decimal.Decimal('0')  # Normal demand

        # Additional adjustment based on recent registration trend
        if recent_registrations > 10:
            adjustment += decimal.Decimal('5')  # Trending up
        elif recent_registrations < 2:
            adjustment -= decimal.Decimal('5')  # Trending down

        # Calculate new price
        adjustment_multiplier = decimal.Decimal('1') + (adjustment / decimal.Decimal('100'))
        new_price = self.base_price * adjustment_multiplier

        # Ensure price stays within min/max bounds
        new_price = max(self.min_price, min(self.max_price, new_price))
        
        return round(new_price, 2)

    @property
    def registration_fee(self):
        """Temporary property to handle transition from registration_fee to base_price"""
        return self.base_price

    @property
    def current_price(self):
        if self.dynamic_pricing_enabled:
            return self.calculate_dynamic_price()
        return self.base_price

    def clean(self):
        if self.dynamic_pricing_enabled:
            # Validate price relationships
            if self.min_price > self.base_price:
                raise ValidationError("Minimum price cannot be greater than base price")
            if self.max_price < self.base_price:
                raise ValidationError("Maximum price cannot be less than base price")
            if self.min_price > self.max_price:
                raise ValidationError("Minimum price cannot be greater than maximum price")
            
            # Validate price increment percentage
            if self.price_increment_percentage < 0 or self.price_increment_percentage > 100:
                raise ValidationError("Price increment percentage must be between 0 and 100")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    qr_code = models.ImageField(upload_to='event_qr_codes/', blank=True, null=True)
    ticket_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    attended = models.BooleanField(default=False)  # New field for attendance

    def __str__(self):
        return f"{self.user.username} - {self.event.name}"

    def save(self, *args, **kwargs):
        if VolunteerRegistration.objects.filter(user=self.user, event=self.event).exists():
            raise ValidationError("Volunteers cannot register as participants for the same event.")
        super().save(*args, **kwargs)

    def generate_qr_code(self):
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(f"Event: {self.event.name}\nTicket ID: {self.ticket_id}\nAttendee: {self.user.get_full_name()}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save QR code image
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f'qr_ticket_{self.ticket_id}.png'
        
        self.qr_code.save(filename, File(buffer), save=True)

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

class EventGalleryItem(models.Model):
    ITEM_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('poster', 'Poster')
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='gallery_items')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='event_gallery/')
    item_type = models.CharField(max_length=10, choices=ITEM_TYPES)
    upload_date = models.DateTimeField(auto_now_add=True)
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-upload_date']
    
    def __str__(self):
        return f"{self.event.name} - {self.title}"
