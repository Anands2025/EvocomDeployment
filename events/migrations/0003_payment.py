# Generated by Django 5.1 on 2024-08-29 05:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0002_event_registration_fee'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('payment_date', models.DateTimeField(auto_now_add=True)),
                ('payment_method', models.CharField(max_length=50)),
                ('transaction_id', models.CharField(max_length=100, unique=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('refunded', 'Refunded')], default='pending', max_length=15)),
                ('event_registration', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='payment', to='events.eventregistration')),
            ],
        ),
    ]
