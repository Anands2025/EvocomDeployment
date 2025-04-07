from django.db import models
from django.conf import settings

from django.db import models
from django.conf import settings

from django.db import models

class CommunityCategory(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=255, default='enabled')

    def __str__(self):
        return self.name


class Community(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    cover = models.ImageField(upload_to='community_covers/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_communities', on_delete=models.CASCADE)
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='admin_communities', on_delete=models.CASCADE)
    category = models.ForeignKey(CommunityCategory, on_delete=models.SET_NULL, null=True, blank=True)
    type=models.CharField(max_length=255, blank=True, null=True)
    tags=models.TextField(blank=True, null=True)
    member_limit = models.PositiveIntegerField(default=50, choices=[(50, '50'), (100, '100'), (250, '250')])

    def __str__(self):
        return self.name

class CommunityTags(models.Model):
    tag_name = models.CharField(max_length=255)
    tag_description=models.TextField()

    def __str__(self):
        return self.tag_name


class UserCommunity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.community.name}"

class CommunityGalleryItem(models.Model):
    ITEM_TYPES = [
        ('image', 'Image'),
        ('video', 'Video')
    ]
    
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='gallery_items')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='community_gallery/')
    item_type = models.CharField(max_length=10, choices=ITEM_TYPES)
    upload_date = models.DateTimeField(auto_now_add=True)
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-upload_date']
    
    def __str__(self):
        return f"{self.community.name} - {self.title}"

class ChatMessage(models.Model):
    STATUS_CHOICES = (
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read')
    )
    
    chat_room = models.ForeignKey('ChatRoom', on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages')
    community = models.ForeignKey('Community', on_delete=models.CASCADE, related_name='chat_messages')
    message = models.TextField()
    file = models.FileField(upload_to='chat_files/', null=True, blank=True)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    is_typing = models.BooleanField(default=False)
    read_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['timestamp']

class ChatRoom(models.Model):
    community = models.ForeignKey('Community', on_delete=models.CASCADE, related_name='chat_rooms')
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_chat_rooms')
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organizer_chat_rooms')
    last_message = models.ForeignKey(ChatMessage, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['community', 'admin', 'organizer']
