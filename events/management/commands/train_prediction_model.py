from django.core.management.base import BaseCommand
from events.prediction import train_prediction_model

class Command(BaseCommand):
    help = 'Trains the event success prediction model'

    def handle(self, *args, **options):
        model, le_event, le_community_category, le_community_name, vectorizer = train_prediction_model()
        if model is None:
            self.stdout.write(self.style.WARNING('Unable to train model. Please ensure you have generated bulk data.'))
        else:
            self.stdout.write(self.style.SUCCESS('Successfully trained prediction model'))