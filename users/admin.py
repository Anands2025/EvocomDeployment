from django.contrib import admin
from . models import EventOrganizers, User,UserDetails,PasswordResetToken
# Register your models here.
admin.site.register(User)
admin.site.register(UserDetails)
admin.site.register(PasswordResetToken)
admin.site.register(EventOrganizers)