# evocom_admin/urls.py

from django.urls import path
from . import views

app_name = 'evocom_admin'

urlpatterns = [
    path('users/', views.user_list, name='user_list'),
    path('communities/', views.community_list, name='community_list'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/edit/<int:category_id>/', views.category_edit, name='category_edit'),
    path('categories/delete/<int:category_id>/', views.category_delete, name='category_delete'),
    path('categories/enable/<int:category_id>/', views.category_enable, name='category_enable'),
    path('tags/', views.tag_list, name='tag_list'),
    path('tags/add/', views.tag_add, name='tag_add'),
    path('tags/edit/<int:tag_id>/', views.tag_edit, name='tag_edit'),
    path('event-categories/', views.event_category_list, name='event_category_list'),
    path('event-categories/add/', views.event_category_add, name='event_category_add'),
    path('event-categories/edit/<int:category_id>/', views.event_category_edit, name='event_category_edit'),
    path('event-categories/delete/<int:category_id>/', views.event_category_delete, name='event_category_delete'),
    path('events/', views.event_list, name='event_list'),
    path('event-categories/enable/<int:category_id>/', views.event_category_enable, name='event_category_enable'),
]
