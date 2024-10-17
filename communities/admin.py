from django.contrib import admin
from .models import Community, CommunityCategory, CommunityTags, UserCommunity

admin.site.register(Community)
admin.site.register(UserCommunity)
admin.site.register(CommunityCategory)
admin.site.register(CommunityTags)
