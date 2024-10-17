from django.core.management.base import BaseCommand
from django.utils import timezone
from events.models import Event
from events.views import send_event_reminder_email

class Command(BaseCommand):
    help = 'Send reminder emails for upcoming events'

    def handle(self, *args, **options):
        now = timezone.now()
        upcoming_events = Event.objects.filter(
            start_datetime__gt=now,
            start_datetime__lte=now + timezone.timedelta(days=1),
            reminder_sent=False
        )

        for event in upcoming_events:
            send_event_reminder_email(event)
            event.reminder_sent = True
            event.save()
            self.stdout.write(self.style.SUCCESS(f'Successfully sent reminders for event "{event.name}"'))
