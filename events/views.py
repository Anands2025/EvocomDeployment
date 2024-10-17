from datetime import datetime
from django.utils import timezone
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import razorpay
from django.contrib import messages
from django.db.models import Sum
from django.template.loader import get_template
from xhtml2pdf import pisa
from openpyxl.styles import Font
import openpyxl
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.text import slugify
import logging
from django.utils.dateparse import parse_datetime
from .prediction import predict_event_success
from django.db import transaction
from io import BytesIO
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

from communities.models import Community, UserCommunity
from .models import Event, EventCategory, EventRegistration, Payment, VolunteerRegistration


@login_required
def create_event(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        
        # Use parse_datetime instead of strptime
        start_datetime = parse_datetime(request.POST.get('start_datetime'))
        end_datetime = parse_datetime(request.POST.get('end_datetime'))
        
        # Make sure the datetimes are timezone-aware
        if start_datetime and not start_datetime.tzinfo:
            start_datetime = timezone.make_aware(start_datetime)
        if end_datetime and not end_datetime.tzinfo:
            end_datetime = timezone.make_aware(end_datetime)
        
        address = request.POST.get('address')
        location = request.POST.get('location')
        location_description = request.POST.get('location_description')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        registration_fee = request.POST.get('registration_fee')
        cover_image = request.FILES.get('cover_image')

        category = get_object_or_404(EventCategory, id=category_id)
        
        event = Event(
            name=name,
            description=description,
            category=category,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            address=address,
            location=location,
            location_description=location_description,
            latitude=latitude,
            longitude=longitude,
            registration_fee=registration_fee,
            organizer=request.user,
            community=community,
            cover_image=cover_image
        )
        event.save()
        return redirect('events:event_management', community_id=community_id)

    categories = EventCategory.objects.filter(status="enabled")
    return render(request, 'events/create_event.html', {'categories': categories, 'community': community})

@login_required
def update_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    categories = EventCategory.objects.filter(status="enabled")

    if request.method == 'POST':
        event.name = request.POST.get('name')
        event.description = request.POST.get('description')
        event.category_id = request.POST.get('category')
        
        # Convert string to datetime object
        start_datetime = datetime.strptime(request.POST.get('start_datetime'), "%Y-%m-%dT%H:%M")
        end_datetime = datetime.strptime(request.POST.get('end_datetime'), "%Y-%m-%dT%H:%M")
        
        # Make the datetime timezone-aware
        event.start_datetime = timezone.make_aware(start_datetime)
        event.end_datetime = timezone.make_aware(end_datetime)
        
        event.address = request.POST.get('address')
        event.location = request.POST.get('location')
        event.location_description = request.POST.get('location_description')
        event.latitude = request.POST.get('latitude')
        event.longitude = request.POST.get('longitude')
        event.registration_fee = request.POST.get('registration_fee')
        
        # Handle cover image update
        new_cover_image = request.FILES.get('cover_image')
        if new_cover_image:
            event.cover_image = new_cover_image
        
        event.save()
        
        return redirect('events:event_management', community_id=event.community.id)

    context = {
        'event': event,
        'categories': categories,
    }
    return render(request, 'events/update_event.html', context)

@login_required
def event_management(request, community_id):
    user = request.user
    community = get_object_or_404(Community, id=community_id)
    
    # Check if the user is a member of the community
    if not UserCommunity.objects.filter(user=user, community=community).exists():
        return HttpResponse('Unauthorized', status=403)
    
    events = Event.objects.filter(organizer=user, community=community)
    return render(request, 'events/event_management.html', {'events': events, 'community': community})


@csrf_exempt
@login_required
def register_for_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')

        if action == 'register_free':
            if event.registration_fee == 0:
                registration = EventRegistration.objects.create(
                    user=request.user,
                    event=event,
                    status='confirmed'
                )
                send_registration_confirmation_email(request.user, event)
                return JsonResponse({'status': 'success', 'message': 'Registered successfully for free event'})
            else:
                return JsonResponse({'status': 'error', 'message': 'This is not a free event'}, status=400)

        elif action == 'create_order':
            # Create Razorpay Order
            order_amount = int(event.registration_fee * 100)  # Convert to paise
            order_currency = 'INR'
            order_receipt = f'order_rcptid_{event.id}_{request.user.id}'
            razorpay_order = client.order.create(dict(
                amount=order_amount,
                currency=order_currency,
                receipt=order_receipt
            ))

            # Create Payment object
            payment = Payment.objects.create(
                event_registration=EventRegistration.objects.create(user=request.user, event=event),
                amount=event.registration_fee,
                order_id=razorpay_order['id'],
                status='pending'
            )

            return JsonResponse({
                'status': 'success',
                'order_id': razorpay_order['id'],
                'amount': order_amount,
                'currency': order_currency,
                'key': settings.RAZORPAY_KEY_ID
            })

        elif action == 'confirm_payment':
            razorpay_payment_id = data.get('razorpay_payment_id')
            razorpay_order_id = data.get('razorpay_order_id')
            razorpay_signature = data.get('razorpay_signature')

            # Verify the payment signature
            try:
                client.utility.verify_payment_signature({
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_payment_id': razorpay_payment_id,
                    'razorpay_signature': razorpay_signature
                })
            except:
                return JsonResponse({'status': 'error', 'message': 'Invalid payment signature'}, status=400)

            # Update Payment object
            try:
                payment = Payment.objects.get(order_id=razorpay_order_id)
                payment.payment_id = razorpay_payment_id
                payment.status = 'completed'
                payment.save()

                # Update EventRegistration status
                payment.event_registration.status = 'confirmed'
                payment.event_registration.save()

                # Send confirmation email in a non-blocking way
                send_registration_confirmation_email(request.user, event)

                return JsonResponse({'status': 'success', 'message': 'Payment confirmed'})
            except Payment.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Payment not found'}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

def upcoming_events(request):
    current_time = datetime.now()
    user_registrations = EventRegistration.objects.filter(user=request.user)
    registered_event_ids = user_registrations.values_list('event_id', flat=True)
    
    events = Event.objects.filter(
        id__in=registered_event_ids,
        status='upcoming'
    ).order_by('start_datetime')
    registered_events = Event.objects.filter(
        id__in=registered_event_ids,
    ).order_by('start_datetime')
    return render(request, 'events/upcoming_events.html', {'events': events, 'registered_events': registered_events})

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    is_registered = False
    is_volunteer = False
    registration = None

    if request.user.is_authenticated:
        registration = EventRegistration.objects.filter(event=event, user=request.user).first()
        is_registered = registration is not None
        is_volunteer = VolunteerRegistration.objects.filter(event=event, user=request.user).exists()

    context = {
        'event': event,
        'is_registered': is_registered,
        'is_volunteer': is_volunteer,
        'registration': registration,
    }
    return render(request, 'events/event_detail.html', context)

@login_required
def event_detail_manage(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.user != event.organizer:
        return redirect('events:event_detail', event_id=event_id)
    
    # Get participants (confirmed registrations)
    participants = EventRegistration.objects.filter(event=event, status='confirmed').select_related('user')
    
    # Get volunteers
    volunteers = VolunteerRegistration.objects.filter(event=event).select_related('user')
    
    # Get payment data
    payments = Payment.objects.filter(event_registration__event=event).select_related('event_registration__user')
    
    # Calculate total payments and amount
    total_payments = payments.count()
    total_amount = payments.aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'event': event,
        'participants': participants,
        'volunteers': volunteers,
        'payments': payments,
        'total_payments': total_payments,
        'total_amount': total_amount,
    }
    return render(request, 'events/event_detail_manage.html', context)



@login_required
def download_participants_pdf(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    participants = EventRegistration.objects.filter(event=event, status='confirmed').select_related('user')
    
    template_path = 'events/participants_pdf.html'
    context = {'event': event, 'participants': participants}
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="participants_{event.name}.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response

@login_required
def check_attendance(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        updated_count = 0
        for key, value in request.POST.items():
            if key.startswith('attendance_'):
                participant_id = key.split('_')[1]
                try:
                    participant = EventRegistration.objects.get(id=participant_id, event=event)
                    participant.attended = value == 'on'
                    participant.save()
                    updated_count += 1
                except EventRegistration.DoesNotExist:
                    messages.warning(request, f"Participant with ID {participant_id} not found.")
        
        messages.success(request, f"Attendance has been updated successfully. {updated_count} records updated.")
    return redirect('events:event_detail_manage', event_id=event.id)


def send_registration_confirmation_email(user, event):
    subject = 'Registration Confirmed for Event: ' + event.name
    context = {'user': user, 'event': event}
    html_content = render_to_string('events/registration_confirmation_email.html', context)
    text_content = strip_tags(html_content)
    send_mail(
        subject,
        text_content,
        settings.EMAIL_HOST_USER,
        [user.email],
        html_message=html_content,
        fail_silently=True,  # This ensures the email sending does not block the response
    )


@login_required
def download_attendance_sheet(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    participants = EventRegistration.objects.filter(event=event, status='confirmed')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance Sheet"

    # Add headers
    headers = ['ID', 'Name', 'Email', 'Phone', 'Attended']
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)

    # Add participant data
    for row, participant in enumerate(participants, start=2):
        ws.cell(row=row, column=1, value=participant.id)
        ws.cell(row=row, column=2, value=f"{participant.user.first_name} {participant.user.last_name}")
        ws.cell(row=row, column=3, value=participant.user.email)
        ws.cell(row=row, column=4, value=participant.user.details.phone_number)
        ws.cell(row=row, column=5, value="")  # Empty cell for marking attendance

    # Generate file name
    file_name = f"attendance_sheet_{slugify(event.name)}.xlsx"

    # Create the HttpResponse object with Excel mime type
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'

    # Save the workbook to the response
    wb.save(response)

    return response

@login_required
def upload_attendance_sheet(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'POST' and request.FILES.get('attendance_file'):
        attendance_file = request.FILES['attendance_file']
        
        try:
            wb = openpyxl.load_workbook(attendance_file)
            ws = wb.active

            updated_count = 0
            for row in ws.iter_rows(min_row=2, values_only=True):
                if len(row) < 5:
                    continue
                participant_id, _, _, _, attended = row
                if participant_id and attended and str(attended).lower() in ['yes', 'y', 'true', '1']:
                    try:
                        registration = EventRegistration.objects.get(id=participant_id, event=event)
                        registration.attended = True
                        registration.save()
                        updated_count += 1
                    except EventRegistration.DoesNotExist:
                        messages.warning(request, f"Participant with ID {participant_id} not found.")

            messages.success(request, f"Attendance has been updated successfully. {updated_count} records updated.")
        except Exception as e:
            messages.error(request, f"An error occurred while processing the file: {str(e)}")
        
    return redirect('events:event_detail_manage', event_id=event.id)


def predict_event_success_view(request):
    if request.method == 'GET':
        event_category = request.GET.get('event_category')
        community_id = request.GET.get('community_id')
        start_datetime_str = request.GET.get('start_datetime')
        end_datetime_str = request.GET.get('end_datetime')
        description = request.GET.get('description', '')
        is_free = request.GET.get('is_free') == 'true'
        
        community = get_object_or_404(Community, id=community_id)
        
        # Use default values if start or end times are not provided
        now = timezone.now()
        start_datetime = parse_datetime(start_datetime_str) if start_datetime_str else now
        end_datetime = parse_datetime(end_datetime_str) if end_datetime_str else (now + timezone.timedelta(hours=1))
        
        predicted_success = predict_event_success(
            event_category=event_category,
            community_category=community.category.name,
            community_name=community.name,
            start_time=start_datetime,
            end_time=end_datetime,
            description=description,
            is_free=is_free
        )
        
        if predicted_success is None:
            return JsonResponse({'error': 'Unable to make prediction. Please ensure you have generated bulk data and trained the model.'}, status=400)
        
        return JsonResponse({'predicted_success': f'{predicted_success:.2%}'})

@login_required
def update_event_metrics(request, event_id=None):
    try:
        with transaction.atomic():
            if event_id:
                events = Event.objects.filter(id=event_id)
            else:
                events = Event.objects.all()

            for event in events:
                actual_attendees = event.get_actual_attendees()
                event.update_success_metrics(actual_attendees)

        return JsonResponse({'status': 'success', 'message': 'Event metrics updated successfully'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def download_invoice(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    registration = get_object_or_404(EventRegistration, user=request.user, event=event)
    payment = get_object_or_404(Payment, event_registration=registration)

    template_path = 'events/invoice_template.html'
    context = {
        'event': event,
        'registration': registration,
        'payment': payment,
        'user': request.user,
        'website_name': 'EvoCom',
        'website_url': 'https://evocom.com',  # Replace with your actual website URL
    }
    return render(request, template_path, context)

def send_event_reminder_email(event):
    subject = f"Reminder: {event.name} is coming up!"
    participants = EventRegistration.objects.filter(event=event, status='confirmed')
    
    for participant in participants:
        context = {
            'user': participant.user,
            'event': event,
        }
        html_content = render_to_string('events/event_reminder_email.html', context)
        text_content = strip_tags(html_content)
        
        send_mail(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [participant.user.email],
            html_message=html_content,
            fail_silently=True,
        )

@login_required
@require_POST
def register_as_volunteer(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if VolunteerRegistration.objects.filter(user=request.user, event=event).exists():
        return JsonResponse({'status': 'error', 'message': "You have already registered as a volunteer for this event."})
    elif EventRegistration.objects.filter(user=request.user, event=event).exists():
        return JsonResponse({'status': 'error', 'message': "You are already registered as a participant for this event."})
    else:
        VolunteerRegistration.objects.create(user=request.user, event=event)
        return JsonResponse({'status': 'success', 'message': "You have successfully registered as a volunteer."})

@login_required
def manage_volunteers(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.user != event.organizer:
        messages.error(request, "You don't have permission to manage volunteers for this event.")
        return redirect('events:event_detail', event_id=event.id)
    
    volunteers = VolunteerRegistration.objects.filter(event=event)
    
    if request.method == 'POST':
        volunteer_id = request.POST.get('volunteer_id')
        action = request.POST.get('action')
        task = request.POST.get('task')
        
        volunteer = get_object_or_404(VolunteerRegistration, id=volunteer_id)
        
        if action == 'approve':
            volunteer.approved = True
            volunteer.save()
            messages.success(request, f"{volunteer.user.username} has been approved as a volunteer.")
        elif action == 'assign_task':
            volunteer.assigned_task = task
            volunteer.save()
            messages.success(request, f"Task assigned to {volunteer.user.username}.")
        elif action == 'remove':
            volunteer.delete()
            messages.success(request, f"{volunteer.user.username} has been removed from volunteers.")
    
    return render(request, 'events/manage_volunteers.html', {'event': event, 'volunteers': volunteers})

@login_required
def approve_volunteer(request, event_id):
    if request.method == 'POST':
        volunteer_id = request.POST.get('volunteer_id')
        volunteer = get_object_or_404(VolunteerRegistration, id=volunteer_id, event_id=event_id)
        if request.user != volunteer.event.organizer:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        volunteer.approved = True
        volunteer.save()
        return JsonResponse({'status': 'success', 'message': 'Volunteer approved successfully'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def assign_task(request, event_id):
    if request.method == 'POST':
        volunteer_id = request.POST.get('volunteer_id')
        task = request.POST.get('task')
        volunteer = get_object_or_404(VolunteerRegistration, id=volunteer_id, event_id=event_id)
        if request.user != volunteer.event.organizer:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        volunteer.assigned_task = task
        volunteer.save()
        return JsonResponse({'status': 'success', 'message': 'Task assigned successfully'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
@require_POST
def remove_volunteer(request, event_id, volunteer_id):
    try:
        event = Event.objects.get(id=event_id)
        volunteer = VolunteerRegistration.objects.get(id=volunteer_id, event=event)
        
        if request.user == event.organizer or request.user.is_superuser:
            volunteer.delete()
            return JsonResponse({'status': 'success', 'message': 'Volunteer removed successfully.'})
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Permission denied. Only the event organizer or superuser can remove volunteers.',
                'user_id': request.user.id,
                'is_superuser': request.user.is_superuser,
                'organizer_id': event.organizer.id
            }, status=403)
    except Event.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Event not found.'}, status=404)
    except VolunteerRegistration.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Volunteer registration not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@require_POST
def email_volunteer(request):
    data = json.loads(request.body)
    email = data.get('email')
    subject = data.get('subject')
    message = data.get('message')
    
    if not all([email, subject, message]):
        return JsonResponse({'status': 'error', 'message': 'Please provide email, subject, and message.'})
    
    try:
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )
        return JsonResponse({'status': 'success', 'message': 'Email sent successfully.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Failed to send email: {str(e)}'})
