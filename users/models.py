from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.utils.crypto import get_random_string

from communities.models import Community


class User(AbstractUser):
    is_google_user = models.BooleanField(default=False)
    pass

class UserDetails(models.Model):
    ROLE_CHOICES = [
        ('member', 'Member'),
        ('organizer', 'Event Organizer'),
        ('community_admin', 'Community Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='details')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    place = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.username

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=100, unique=True)
    expiry = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = get_random_string(length=32)
        if not self.expiry:
            self.expiry = timezone.now() + timedelta(minutes=15)
        super().save(*args, **kwargs)

    def is_valid(self):
        return self.expiry > timezone.now()

    def __str__(self):
        return f"Token for {self.user.username} expires at {self.expiry}"
class EventOrganizers(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='organizer')
    status=models.CharField(max_length=100, null=True,blank=True)
    
 # Adjust import as needed

class EventOrganizerRequest(models.Model):
    member = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.username} - {self.community.name} - {self.status}"


from django_otp.plugins.otp_totp.models import TOTPDevice

class UserTwoFactor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='two_factor')
    is_enabled = models.BooleanField(default=False)
    backup_codes = models.JSONField(default=list)
    
    def generate_backup_codes(self):
        codes = [get_random_string(8) for _ in range(5)]
        self.backup_codes = codes
        self.save()
        return codes