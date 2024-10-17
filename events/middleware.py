import time
from django.utils import timezone
from .utils import check_and_send_reminders

class ReminderMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.last_check = timezone.now()

    def __call__(self, request):
        now = timezone.now()
        if (now - self.last_check).total_seconds() > 3600:  # Check every hour
            check_and_send_reminders()
            self.last_check = now

        response = self.get_response(request)
        return response