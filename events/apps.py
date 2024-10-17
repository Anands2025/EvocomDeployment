from django.apps import AppConfig
from django.core.management import call_command


class EventsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'events'

    def ready(self):
        # Import and run the command
        from django.core.management import call_command
        call_command('update_event_status')
        call_command('train_prediction_model')
