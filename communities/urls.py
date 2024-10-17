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
]