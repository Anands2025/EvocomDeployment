from pyexpat.errors import messages
from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from events.models import Event, EventRegistration, Payment
from users.models import EventOrganizerRequest
from .models import Community, CommunityCategory, UserCommunity

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
    user=request.user
    community = Community.objects.get(admin=user)
    categories = CommunityCategory.objects.all()
    context = {
        'categories': categories,
        'community': community
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
