from django.urls import path
from . import views

app_name = 'events' 
urlpatterns = [
    path('manage_events/<int:community_id>/', views.event_management, name='event_management'),
    path('create_event/<int:community_id>/', views.create_event, name='create_event'),
    path('update/<int:event_id>/', views.update_event, name='update_event'),
    path('register/<int:event_id>/', views.register_for_event, name='register_for_event'),
    path('upcoming_events/', views.upcoming_events, name='upcoming_events'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
    path('event/<int:event_id>/manage/', views.event_detail_manage, name='event_detail_manage'),
    path('event/<int:event_id>/download_participants_pdf/', views.download_participants_pdf, name='download_participants_pdf'),
    path('event/<int:event_id>/check-attendance/', views.check_attendance, name='check_attendance'),
    path('event/<int:event_id>/download-attendance/', views.download_attendance_sheet, name='download_attendance_sheet'),
    path('predict-success/', views.predict_event_success_view, name='predict_success'),
    path('update-metrics/<int:event_id>/', views.update_event_metrics, name='update_event_metrics'),
    path('update-all-metrics/', views.update_event_metrics, name='update_all_event_metrics'),
    path('download_invoice/<int:event_id>/', views.download_invoice, name='download_invoice'),
    path('event/<int:event_id>/approve-volunteer/', views.approve_volunteer, name='approve_volunteer'),
    path('event/<int:event_id>/assign-task/', views.assign_task, name='assign_task'),
    path('event/<int:event_id>/remove-volunteer/<int:volunteer_id>/', views.remove_volunteer, name='remove_volunteer'),
    path('register-volunteer/<int:event_id>/', views.register_as_volunteer, name='register_as_volunteer'),
    path('email-volunteer/', views.email_volunteer, name='email_volunteer'),
    # Remove the separate upload_attendance_sheet URL if it exists
]
