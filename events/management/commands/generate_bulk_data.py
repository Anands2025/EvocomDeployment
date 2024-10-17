from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count
from events.models import Event, EventCategory, EventSuccessMetrics
from communities.models import Community, CommunityCategory
from users.models import User
import random
from datetime import timedelta

class Command(BaseCommand):
    help = 'Generates bulk data for event success prediction'

    def handle(self, *args, **options):
        self.stdout.write('Starting bulk data generation...')

        # Check if we have necessary base data
        self.check_base_data()

        # Generate bulk event data
        self.generate_events(1000)  # Generate 1000 events

        self.stdout.write(self.style.SUCCESS('Successfully generated bulk data'))

    def check_base_data(self):
        if EventCategory.objects.count() == 0:
            self.stdout.write(self.style.WARNING('No event categories found. Please create some event categories before running this command.'))
            return

        if CommunityCategory.objects.count() == 0:
            self.stdout.write(self.style.WARNING('No community categories found. Please create some community categories before running this command.'))
            return

        if Community.objects.count() == 0:
            self.stdout.write(self.style.WARNING('No communities found. Creating sample communities...'))
            self.create_sample_communities()

    def create_sample_communities(self):
        admin_user = User.objects.first()  # Assuming you have at least one user
        for category in CommunityCategory.objects.all():
            Community.objects.create(
                name=f'{category.name} Community',
                description=f'A community for {category.name} enthusiasts',
                created_by=admin_user,
                admin=admin_user,
                category=category
            )
        self.stdout.write(self.style.SUCCESS('Created sample communities'))

    def generate_events(self, num_events):
        communities = Community.objects.all()
        event_categories = EventCategory.objects.all()
        
        for _ in range(num_events):
            community = random.choice(communities)
            category = random.choice(event_categories)
            
            start_datetime = timezone.now() + timezone.timedelta(days=random.randint(1, 365))
            duration_hours = random.uniform(1, 8)  # Events last between 1 and 8 hours
            end_datetime = start_datetime + timezone.timedelta(hours=duration_hours)
            
            is_free = random.choice([True, False])
            registration_fee = 0 if is_free else random.randint(500, 5000)
            
            event = Event.objects.create(
                name=self.generate_event_name(category, community),
                description=self.generate_event_description(category, community),
                category=category,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                address=self.generate_address(),
                community=community,
                organizer=community.admin,
                registration_fee=registration_fee
            )
            
            # Generate random success metrics
            attendance_ratio = self.generate_attendance_ratio(category, community, is_free, start_datetime.weekday())
            
            EventSuccessMetrics.objects.create(
                event=event,
                attendance_ratio=attendance_ratio,
                event_category=category.name,
                community_category=community.category.name,
                community_name=community.name,
                is_synthetic=True
            )

        self.stdout.write(f'Generated {num_events} events with success metrics')

    def generate_event_name(self, category, community):
        adjectives = ['Annual', 'Quarterly', 'Monthly', 'Weekly', 'Special', 'Exclusive', 'Premier']
        return f'{random.choice(adjectives)} {category.name} for {community.name}'

    def generate_event_description(self, category, community):
        return f'Join us for an exciting {category.name} event tailored for the {community.name} community. ' \
               f'This event promises to bring together enthusiasts and experts in {community.category.name}.'

    def generate_address(self):
        streets = ['Main St', 'Broadway', 'Park Ave', 'Oak Lane', 'Cedar Rd']
        cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix']
        return f'{random.randint(100, 999)} {random.choice(streets)}, {random.choice(cities)}'

    def generate_attendance_ratio(self, category, community, is_free, day_of_week):
        base_ratio = random.uniform(0.5, 0.9)
        category_factor = random.uniform(0.9, 1.1)
        community_factor = random.uniform(0.9, 1.1)
        free_factor = 1.1 if is_free else 0.9
        weekend_factor = 1.1 if day_of_week >= 5 else 1.0
        return min(base_ratio * category_factor * community_factor * free_factor * weekend_factor, 1.0)