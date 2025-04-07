from django.urls import path
from . import views

app_name = 'communities' 
urlpatterns = [
    path('create_community/', views.create_community, name='create_community'),
    path('community_management/', views.community_management, name='community_management'),
    path('community/members/', views.community_members, name='community_members'),
    path('community/<int:community_id>/remove_member/<int:user_id>/', views.remove_member, name='remove_member'),
    path('update_community/', views.update_community, name='update_community'),
    path('show_communities/',views.show_communities, name='show_communities'),
    path('community/<int:pk>/', views.view_community, name='view_community'),
    path('community/<int:community_id>/join/', views.join_community, name='join_community'),
    path('joined_communities/',views.joined_communities, name='joined_communities'),
    path('event-organizer-requests/', views.event_organizer_requests, name='event_organizer_requests'),
    path('approve-request/<int:request_id>/', views.approve_request, name='approve_request'),
    path('reject-request/<int:request_id>/', views.reject_request, name='reject_request'),
    path('community/<int:community_id>/gallery/upload/', views.upload_gallery_item, name='upload_gallery_item'),
    path('community/<int:community_id>/gallery/<int:item_id>/delete/', views.delete_gallery_item, name='delete_gallery_item'),
    path('chat/', views.chat_view, name='chat'),
    path('chat/<int:room_id>/messages/', views.get_messages, name='get_messages'),
    path('chat/<int:room_id>/send/', views.send_message, name='send_message'),
    path('organizer-chat/', views.organizer_chat, name='organizer_chat'),
    path('chat/<int:room_id>/typing/', views.typing_status, name='typing_status'),
    path('chat/<int:room_id>/status/', views.message_status, name='message_status'),
    path('statistics/<int:community_id>/', views.community_statistics, name='community_statistics'),
    path('events-list/<int:community_id>/', views.community_events_list, name='community_events_list'),
    path('community/<int:community_id>/event-report/', views.generate_event_report, name='generate_event_report'),
]