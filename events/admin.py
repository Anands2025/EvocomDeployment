from django.contrib import admin
from .models import EventCategory, EventSubCategory, Event, Task, EventRegistration

admin.site.register(EventCategory)
admin.site.register(EventSubCategory)
admin.site.register(Event)
admin.site.register(Task)
admin.site.register(EventRegistration)


class EventAdmin(admin.ModelAdmin):
    # ... other configurations ...

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.set_lat_long()

