from django.core.management.base import BaseCommand
from django.utils import timezone
from events.models import Event

class Command(BaseCommand):
    help = 'Updates event statuses based on current date'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Update ongoing events
        ongoing_count = Event.objects.filter(
            status='upcoming',
            start_datetime__lte=now,
            end_datetime__gt=now
        ).update(status='ongoing')

        # Update completed events
        completed_count = Event.objects.filter(
            status__in=['upcoming', 'ongoing'],
            end_datetime__lte=now
        ).update(status='completed')

        self.stdout.write(self.style.SUCCESS(f'Successfully updated event statuses. {ongoing_count} set to ongoing, {completed_count} set to completed.'))