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
