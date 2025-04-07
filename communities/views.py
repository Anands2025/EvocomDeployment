from pyexpat.errors import messages
from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Avg, Count, Sum
from django.db.models.functions import TruncMonth, ExtractYear, ExtractMonth
from events.models import Event, EventRegistration, Payment, EventSuccessMetrics
from users.models import EventOrganizerRequest
from .models import Community, CommunityCategory, UserCommunity, CommunityGalleryItem, ChatRoom, ChatMessage
from django.http import JsonResponse
import json
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
import logging
from django.core.cache import cache
import pytz
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.http import HttpResponse

User = get_user_model()
logger = logging.getLogger(__name__)

@login_required
def create_community(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        cover = request.FILES.get('cover')
        category_id = request.POST.get('category')
        category = CommunityCategory.objects.get(id=category_id) if category_id else None
        type = request.POST.get('type')
        member_limit = request.POST.get('member_limit')
        community = Community(
            name=name,
            description=description,
            created_by=request.user,
            admin=request.user,
            cover=cover,
            category=category,
            type=type,
            member_limit=member_limit,
        )
        community.save()
        return redirect('users:community_admin_index')

    categories = CommunityCategory.objects.get()
    context = {
        'categories': categories
    }
    return render(request, 'communities/create_community.html', context)


@login_required
def update_community(request):
    user = request.user
    community = Community.objects.get(admin=user)
    categories = CommunityCategory.objects.all()  # Fetch all categories

    if request.method == 'POST':
        name = request.POST.get('community_name')
        description = request.POST.get('community_description')
        category_id = request.POST.get('category')  # Fetch selected category ID
        cover = request.FILES.get('cover_image')
        type = request.POST.get('type')
        member_limit = request.POST.get('member_limit')
        # Update the community instance
        community.name = name
        community.description = description
        community.category_id = category_id
        community.type =type
        community.member_limit = member_limit
        if cover:
            community.cover = cover
        community.save()

        return redirect('communities:community_management')

@login_required
def community_management(request):
    community = get_object_or_404(Community, admin=request.user)
    
    # Get unread messages count from event organizers
    unread_messages_count = ChatMessage.objects.filter(
        community=community,
        receiver=request.user,
        is_read=False
    ).count()
    
    context = {
        'community': community,
        'unread_messages_count': unread_messages_count,
        'categories': CommunityCategory.objects.all(),
    }
    return render(request, 'communities/community_management.html', context)

@login_required
def show_communities(request):
    communities = Community.objects.all()
    return render(request, 'communities/show_communities.html', {'communities': communities})


@login_required
def view_community(request, pk):
    community = get_object_or_404(Community, pk=pk)
    is_member = UserCommunity.objects.filter(user=request.user, community=community).exists()
    members = UserCommunity.objects.filter(community=community)
    
    pending_request = EventOrganizerRequest.objects.filter(
        member=request.user,
        community=community,
        status='pending'
    ).exists()
    
    approved_request = EventOrganizerRequest.objects.filter(
        member=request.user,
        community=community,
        status='approved'
    ).exists()
    
    # Fetch both upcoming and past events
    now = timezone.now()
    upcoming_events = Event.objects.filter(
        community=community, 
        end_datetime__gte=now
    ).order_by('start_datetime')
    
    past_events = Event.objects.filter(
        community=community, 
        end_datetime__lt=now
    ).order_by('-start_datetime')  # Note the minus sign for descending order

    all_events = list(upcoming_events) + list(past_events)

    user_event_registrations = EventRegistration.objects.filter(
        user=request.user,
        event__in=all_events
    ).select_related('payment')
    
    registered_events = {}
    for registration in user_event_registrations:
        registered_events[registration.event_id] = {
            'is_registered': True,
            'payment': registration.payment if hasattr(registration, 'payment') else None
        }
    
    for event in all_events:
        event_data = registered_events.get(event.id, {'is_registered': False, 'payment': None})
        event.is_registered = event_data['is_registered']
        event.user_payment = event_data['payment']

    context = {
        'community': community,
        'is_member': is_member,
        'members': members,
        'pending_request': pending_request,
        'approved_request': approved_request,
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'RAZORPAY_KEY_ID': settings.RAZORPAY_KEY_ID,
    }

    return render(request, 'communities/view_community.html', context)


@login_required
def join_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    UserCommunity.objects.get_or_create(user=request.user, community=community)
    return redirect('communities:view_community', pk=community.id)

@login_required
def joined_communities(request):
    user = request.user
    communities = Community.objects.filter(usercommunity__user=user)
    return render(request, 'communities/joined_communities.html', {'communities': communities})
@login_required
def community_members(request):
    user = request.user
    community = Community.objects.get(admin=user)
    members = UserCommunity.objects.filter(community=community)

    context = {
        'community': community,
        'members': members
    }

    return render(request, 'communities/community_members.html', context)
@login_required
def remove_member(request, community_id, user_id):
    if request.method == 'POST':
        community = get_object_or_404(Community, pk=community_id)
        user_community = get_object_or_404(UserCommunity, community=community, user_id=user_id)
        user_community.delete()
        
    return redirect('communities:community_members')

@login_required
def event_organizer_requests(request):
    """View to list all event organizer requests."""
    user = request.user
    community = Community.objects.get(admin=user)
    requests = EventOrganizerRequest.objects.filter(community=community)
    return render(request, 'communities/event_organizer_requests.html', {'requests': requests})

@login_required
def approve_request(request, request_id):
    """View to approve an event organizer request."""
    organizer_request = get_object_or_404(EventOrganizerRequest, id=request_id)
    organizer_request.status = 'approved'  # Update the status to 'approved'
    organizer_request.save()
    return redirect('communities:event_organizer_requests')

@login_required
def reject_request(request, request_id):
    """View to reject an event organizer request."""
    organizer_request = get_object_or_404(EventOrganizerRequest, id=request_id)
    organizer_request.status = 'rejected'  # Update the status to 'rejected'
    organizer_request.save()
    return redirect('communities:event_organizer_requests')

@login_required
def upload_gallery_item(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    
    # Check if user is community admin
    if community.admin != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            description = request.POST.get('description', '')
            item_type = request.POST.get('item_type')
            file = request.FILES.get('file')
            is_featured = request.POST.get('is_featured') == 'true'
            
            if not all([title, item_type, file]):
                return JsonResponse({'error': 'Missing required fields'}, status=400)
            
            gallery_item = CommunityGalleryItem.objects.create(
                community=community,
                title=title,
                description=description,
                file=file,
                item_type=item_type,
                is_featured=is_featured
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Gallery item uploaded successfully',
                'item': {
                    'id': gallery_item.id,
                    'title': gallery_item.title,
                    'url': gallery_item.file.url
                }
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def delete_gallery_item(request, community_id, item_id):
    gallery_item = get_object_or_404(CommunityGalleryItem, id=item_id, community_id=community_id)
    
    # Check if user is community admin
    if gallery_item.community.admin != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            gallery_item.file.delete(save=False)
            gallery_item.delete()
            return JsonResponse({
                'success': True,
                'message': 'Gallery item deleted successfully'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def chat_view(request):
    user = request.user
    
    # For community admins: get all chat rooms with event organizers
    if user.admin_communities.exists():
        # Get all approved event organizers for admin's communities
        admin_communities = user.admin_communities.all()
        event_organizers = User.objects.filter(
            eventorganizerrequest__community__in=admin_communities,
            eventorganizerrequest__status='approved'
        ).distinct()
        
        # Get or create chat rooms for each organizer
        chat_rooms = []
        for community in admin_communities:
            community_organizers = event_organizers.filter(
                eventorganizerrequest__community=community
            )
            for organizer in community_organizers:
                chat_room, created = ChatRoom.objects.get_or_create(
                    community=community,
                    admin=user,
                    organizer=organizer
                )
                chat_rooms.append(chat_room)
        
        chat_rooms = ChatRoom.objects.filter(
            id__in=[room.id for room in chat_rooms]
        ).select_related('community', 'admin', 'organizer')
    
    # For event organizers: get chat rooms with community admins
    else:
        organizer_communities = Community.objects.filter(
            eventorganizerrequest__member=user,
            eventorganizerrequest__status='approved'
        )
        chat_rooms = ChatRoom.objects.filter(
            community__in=organizer_communities,
            organizer=user
        ).select_related('community', 'admin', 'organizer')
    
    # Get unread message counts
    for room in chat_rooms:
        room.unread_count = ChatMessage.objects.filter(
            chat_room=room,
            receiver=user,
            is_read=False
        ).count()
    
    context = {
        'chat_rooms': chat_rooms,
        'current_room': chat_rooms.first() if chat_rooms.exists() else None,
        'messages': ChatMessage.objects.filter(chat_room=chat_rooms.first()).order_by('timestamp') if chat_rooms.exists() else [],
        'is_admin': user.admin_communities.exists()
    }
    
    return render(request, 'communities/chat.html', context)

@login_required
def get_messages(request, room_id):
    chat_room = get_object_or_404(ChatRoom, id=room_id)
    messages = ChatMessage.objects.filter(chat_room=chat_room).order_by('timestamp')
    
    # Mark received messages as read
    unread_messages = messages.filter(receiver=request.user, is_read=False)
    current_time = timezone.now()
    unread_messages.update(is_read=True, status='read', read_time=current_time)
    
    ist = pytz.timezone('Asia/Kolkata')
    messages_data = [{
        'id': msg.id,
        'message': msg.message,
        'timestamp': msg.timestamp.astimezone(ist).strftime('%I:%M %p'),
        'is_sent': msg.sender == request.user,
        'file_url': msg.file.url if msg.file else None,
        'file_name': msg.file_name if msg.file else None,
        'status': msg.status,
        'read_time': msg.read_time.astimezone(ist).strftime('%I:%M %p') if msg.read_time else None
    } for msg in messages]
    
    return JsonResponse({'messages': messages_data})

@login_required
@require_POST
def send_message(request, room_id):
    chat_room = get_object_or_404(ChatRoom, id=room_id)
    
    # Verify user is part of the chat room
    if request.user != chat_room.admin and request.user != chat_room.organizer:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        message_text = request.POST.get('message', '').strip()
        file = request.FILES.get('file')
        
        if not message_text and not file:
            return JsonResponse({'error': 'Message or file is required'}, status=400)
        
        # Determine receiver
        receiver = chat_room.organizer if request.user == chat_room.admin else chat_room.admin
        
        message = ChatMessage.objects.create(
            chat_room=chat_room,
            sender=request.user,
            receiver=receiver,
            message=message_text,
            community=chat_room.community,
            is_read=False
        )

        if file:
            message.file = file
            message.file_name = file.name
            message.save()
        
        ist = pytz.timezone('Asia/Kolkata')
        return JsonResponse({
            'status': 'success',
            'message': {
                'id': message.id,
                'message': message.message,
                'timestamp': message.timestamp.astimezone(ist).strftime('%I:%M %p'),
                'sender_name': message.sender.get_full_name() or message.sender.username,
                'is_sent': True,
                'file_url': message.file.url if message.file else None,
                'file_name': message.file_name if message.file else None,
                'status': 'sent'
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def organizer_chat(request):
    user = request.user
    
    # Get communities where user is an approved event organizer
    organizer_communities = Community.objects.filter(
        eventorganizerrequest__member=user,
        eventorganizerrequest__status='approved'
    )
    
    chat_rooms = ChatRoom.objects.filter(
        community__in=organizer_communities,
        organizer=user
    ).select_related('community', 'admin', 'organizer')
    
    # Create chat rooms if they don't exist
    for community in organizer_communities:
        ChatRoom.objects.get_or_create(
            community=community,
            admin=community.admin,
            organizer=user
        )
    
    # Refresh chat rooms list after creating new ones
    chat_rooms = ChatRoom.objects.filter(
        community__in=organizer_communities,
        organizer=user
    ).select_related('community', 'admin', 'organizer')
    
    # Get unread message counts
    for room in chat_rooms:
        room.unread_count = ChatMessage.objects.filter(
            chat_room=room,
            receiver=user,
            is_read=False
        ).count()
    
    context = {
        'chat_rooms': chat_rooms,
        'current_room': chat_rooms.first() if chat_rooms.exists() else None,
        'messages': ChatMessage.objects.filter(chat_room=chat_rooms.first()).order_by('timestamp') if chat_rooms.exists() else [],
        'is_admin': False
    }
    
    return render(request, 'communities/organizer_chat.html', context)

@login_required
@require_POST
def typing_status(request, room_id):
    chat_room = get_object_or_404(ChatRoom, id=room_id)
    is_typing = request.POST.get('is_typing') == 'true'
    
    # Update user's typing status in cache or database
    cache.set(f'typing_{room_id}_{request.user.id}', is_typing, 5)  # Expires after 5 seconds
    
    return JsonResponse({'status': 'success'})

@login_required
def message_status(request, room_id):
    chat_room = get_object_or_404(ChatRoom, id=room_id)
    
    # Get typing status
    other_user = chat_room.organizer if request.user == chat_room.admin else chat_room.admin
    is_typing = cache.get(f'typing_{room_id}_{other_user.id}', False)
    
    # Update message statuses
    unread_messages = ChatMessage.objects.filter(
        chat_room=chat_room,
        receiver=request.user,
        is_read=False
    )
    
    # Mark messages as read
    unread_messages.update(status='read', is_read=True)
    
    # Get status updates for sent messages
    sent_messages = ChatMessage.objects.filter(
        chat_room=chat_room,
        sender=request.user
    ).values('id', 'status')
    
    return JsonResponse({
        'is_typing': is_typing,
        'message_statuses': list(sent_messages)
    })

@login_required
def community_statistics(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    
    # Check if user is admin
    if not community.admin == request.user:
        messages.error(request, "You don't have permission to view these statistics.")
        return redirect('communities:view_community', pk=community_id)
    
    # Get all events for this community
    events = Event.objects.filter(community=community)
    
    # Basic statistics
    total_events = events.count()
    total_registrations = EventRegistration.objects.filter(event__community=community).count()
    total_revenue = Payment.objects.filter(
        event_registration__event__community=community, 
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Event category distribution
    category_stats = events.values('category__name').annotate(
        count=Count('id'),
        avg_attendance=Avg('success_metrics__attendance_ratio')
    )
    
    # Timeline analysis - modified to handle None values
    events_by_month = (
        Event.objects.filter(community_id=community_id)
        .annotate(
            year=ExtractYear('start_datetime'),
            month=ExtractMonth('start_datetime')
        )
        .values('year', 'month')
        .annotate(count=Count('id'))
        .order_by('year', 'month')
    )

    # Format the data for the template with error handling
    events_by_month = [
        {
            'month': f"{item['year']}-{item['month']:02d}-01" if item['year'] and item['month'] else None,
            'count': item['count']
        }
        for item in events_by_month
        if item['year'] is not None and item['month'] is not None  # Filter out entries with None values
    ]
    
    # Success metrics analysis
    success_metrics = EventSuccessMetrics.objects.filter(
        event__community=community
    ).aggregate(
        avg_attendance_ratio=Avg('attendance_ratio'),
        weekend_events=Count('id', filter=Q(is_weekend=True)),
        weekday_events=Count('id', filter=Q(is_weekend=False))
    )
    
    # Calculate free vs paid events
    free_events_count = events.filter(base_price=0).count()
    paid_events_count = events.exclude(base_price=0).count()
    
    context = {
        'community': community,
        'total_events': total_events,
        'total_registrations': total_registrations,
        'total_revenue': total_revenue,
        'category_stats': category_stats,
        'events_by_month': events_by_month,
        'success_metrics': success_metrics,
        'free_events_count': free_events_count,
        'paid_events_count': paid_events_count,
    }
    
    return render(request, 'communities/statistics.html', context)

@login_required
def community_events_list(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    current_time = timezone.now()
    
    # Get all events for this community
    events = Event.objects.filter(community=community)
    
    # Categorize events
    completed_events = events.filter(
        end_datetime__lt=current_time
    ).order_by('-end_datetime')
    
    ongoing_events = events.filter(
        start_datetime__lte=current_time,
        end_datetime__gte=current_time
    ).order_by('end_datetime')
    
    upcoming_events = events.filter(
        start_datetime__gt=current_time
    ).order_by('start_datetime')
    
    # Get registration counts for each event
    for event in completed_events:
        event.registration_count = EventRegistration.objects.filter(event=event).count()
        event.revenue = Payment.objects.filter(
            event_registration__event=event,
            status='completed'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    for event in ongoing_events:
        event.registration_count = EventRegistration.objects.filter(event=event).count()
    
    for event in upcoming_events:
        event.registration_count = EventRegistration.objects.filter(event=event).count()
    
    context = {
        'community': community,
        'completed_events': completed_events,
        'ongoing_events': ongoing_events,
        'upcoming_events': upcoming_events,
    }
    
    return render(request, 'communities/events_list.html', context)

@login_required
def generate_event_report(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    current_time = timezone.now()
    
    # Get all completed events for this community
    completed_events = Event.objects.filter(
        community=community,
        end_datetime__lt=current_time
    ).order_by('-end_datetime')
    
    # Calculate statistics for each event using existing methods
    total_revenue = 0
    total_attendance_rate = 0
    total_events = completed_events.count()
    
    for event in completed_events:
        event.total_registrations = event.get_total_registrations()
        event.attended_count = event.get_actual_attendees()
        event.total_revenue = Payment.objects.filter(
            event_registration__event=event,
            status='completed'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_revenue += event.total_revenue
        event.attendance_rate = (event.attended_count / event.total_registrations * 100) if event.total_registrations > 0 else 0
        total_attendance_rate += event.attendance_rate
    
    average_attendance_rate = total_attendance_rate / total_events if total_events > 0 else 0
    
    # Create the PDF using xhtml2pdf
    template = get_template('communities/event_report.html')
    context = {
        'community': community,
        'events': completed_events,
        'generated_date': current_time,
        'total_revenue': total_revenue,
        'average_attendance_rate': average_attendance_rate,
    }
    html = template.render(context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{community.name}_event_report.pdf"'
    
    # Convert HTML to PDF
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating PDF', status=500)
    
    return response
