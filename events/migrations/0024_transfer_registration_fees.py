from django.db import migrations

def transfer_registration_fees(apps, schema_editor):
    Event = apps.get_model('events', 'Event')
    for event in Event.objects.all():
        if event.registration_fee is not None:
            event.base_price = event.registration_fee
            event.min_price = event.registration_fee
            event.max_price = event.registration_fee
            event.save()

def reverse_transfer(apps, schema_editor):
    Event = apps.get_model('events', 'Event')
    for event in Event.objects.all():
        if event.base_price is not None:
            event.registration_fee = event.base_price
            event.save()

class Migration(migrations.Migration):
    dependencies = [
        ('events', '0023_event_base_price_event_dynamic_pricing_enabled_and_more'),
    ]

    operations = [
        migrations.RunPython(transfer_registration_fees, reverse_transfer),
        migrations.RemoveField(
            model_name='event',
            name='registration_fee',
        ),
    ] 