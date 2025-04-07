from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import ChatMessage
from events.models import Event
from communities.models import Community, UserCommunity, CommunityCategory
from users.models import EventOrganizers, EventOrganizerRequest
from django.db.models import Count
import json
import requests
import logging
from django.utils import timezone

# Set up logging
logger = logging.getLogger(__name__)

def get_bot_response(message, context=""):
    """Get response from HuggingFace API using Mistral"""
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    
    # Concise base prompt
    system_prompt = """You are EvoCom Assistant, a helpful AI for the EvoCom community platform. 
    EvoCom helps users create and join communities, organize events, and connect with others.
    Provide friendly, concise responses."""
    
    # Add detailed information only for specific queries
    if any(keyword in message.lower() for keyword in ['how to', 'what is', 'explain', 'help']):
        system_prompt += """

        Key Features:
        - Community Management: Create, join, and manage communities
        - Event Organization: Create events, track attendance
        - User Roles: Members, Organizers, Admins
        - Profile Management: Update info, security settings"""
    
    full_message = f"""<s>[INST] {system_prompt}

    Context:
    {context}
    
    User Message: {message}[/INST]</s>"""
    
    try:
        response = requests.post(
            settings.HUGGINGFACE_API_URL,
            headers=headers,
            json={
                "inputs": full_message,
                "parameters": {
                    "max_new_tokens": 150,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "return_full_text": False,
                    "do_sample": True
                }
            }
        )
        
        if response.status_code == 200:
            bot_response = response.json()[0]['generated_text']
            bot_response = bot_response.replace("[/INST]", "").replace("[INST]", "").strip()
            return bot_response, 'success'
        else:
            logger.error(f"API Error: {response.status_code} - {response.text}")
            return "I'm having trouble processing your request. Please try again.", 'error'
            
    except Exception as e:
        logger.error(f"Error calling HuggingFace API: {str(e)}")
        return "Sorry, I'm having technical difficulties. Please try again later.", 'error'

@login_required
@require_POST
def chat_message(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '')
        user = request.user
        
        # Get basic user context
        user_communities = Community.objects.filter(usercommunity__user=user)
        upcoming_events = Event.objects.filter(
            community__in=user_communities,
            end_datetime__gte=timezone.now()
        ).order_by('start_datetime')[:3]
        
        # Get community categories
        community_categories = CommunityCategory.objects.filter(
            community__in=user_communities
        ).distinct()
        
        # Get user's roles in communities
        admin_communities = Community.objects.filter(admin=user)
        created_communities = Community.objects.filter(created_by=user)
        
        # Get user's event organizer status
        is_event_organizer = EventOrganizers.objects.filter(user=user, status='active').exists()
        organizer_requests = EventOrganizerRequest.objects.filter(member=user)
        
        # Create comprehensive context
        context = f"""
        User Information:
        - Name: {user.first_name} {user.last_name}
        - Platform Role: {user.details.role if hasattr(user, 'details') else 'Member'}
        - Email: {user.email}
        - Join Date: {user.date_joined.strftime('%Y-%m-%d')}

        Community Engagement:
        - Total Communities: {user_communities.count()}
        - Admin of Communities: {admin_communities.count()}
        - Created Communities: {created_communities.count()}
        - Community Categories: {', '.join([cat.name for cat in community_categories])}
        - Communities: {', '.join([f"{c.name} ({'Admin' if c in admin_communities else 'Member'})" for c in user_communities[:3]])}

        Event Information:
        - Event Organizer Status: {'Active' if is_event_organizer else 'Not an organizer'}
        - Pending Organizer Requests: {organizer_requests.filter(status='pending').count()}
        - Approved Organizer Requests: {organizer_requests.filter(status='approved').count()}
        - Upcoming Events: {', '.join([f"{e.name} on {e.start_datetime.strftime('%Y-%m-%d')}" for e in upcoming_events]) if upcoming_events else 'None scheduled'}
        
        Platform Features:
        - Community Management: Create, join, and manage communities
        - Event Organization: Create and manage events, track attendance
        - Volunteer Management: Register as volunteer, assign tasks
        - Member Networking: Connect with community members
        - Discussion Forums: Engage in community discussions
        - Resource Sharing: Share and access community resources
        """
        
        # Add specific context based on user's query
        if 'community' in user_message.lower():
            context += f"\nCommunity Focus: Managing {admin_communities.count()} communities, member of {user_communities.count() - admin_communities.count()} others"
        elif 'event' in user_message.lower():
            context += f"\nEvent Focus: {'Can organize events' if is_event_organizer else 'Can participate in events'}"
        elif 'profile' in user_message.lower():
            context += f"\nProfile Focus: Platform role is {user.details.role if hasattr(user, 'details') else 'Member'}"
        elif 'admin' in user_message.lower():
            context += f"\nAdmin Focus: Administrator of {admin_communities.count()} communities"
        
        bot_response, status = get_bot_response(user_message, context)
        
        ChatMessage.objects.create(
            user=user,
            message=user_message,
            response=bot_response
        )
        
        return JsonResponse({
            'response': bot_response,
            'status': status
        })

    except Exception as e:
        logger.error(f"Unexpected error in chat_message: {str(e)}")
        return JsonResponse({
            'response': "Sorry, I encountered an unexpected error. Please try again.",
            'status': 'error'
        })

def get_context_data(user):
    """
    Gather relevant context data for the user to help provide better responses.
    """
    context = {
        "user_info": {
            "name": f"{user.first_name} {user.last_name}",
            "role": user.details.role,
        }
    }
    
    try:
        # Get user's communities
        joined_communities = user.joined_communities.all()
        context["communities"] = [
            {"name": comm.name, "role": comm.get_user_role(user)}
            for comm in joined_communities
        ]
        
        # Get upcoming events
        upcoming_events = Event.objects.filter(
            community__in=joined_communities,
            start_date__gte=timezone.now()
        )[:5]
        context["upcoming_events"] = [
            {"name": event.name, "date": event.start_date}
            for event in upcoming_events
        ]
        
    except Exception as e:
        logger.error(f"Error gathering context data: {str(e)}")
    
    return context
