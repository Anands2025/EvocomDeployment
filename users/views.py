from django.contrib.auth import authenticate, login, logout,update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.crypto import get_random_string
from evocom import settings
from .models import EventOrganizerRequest, EventOrganizers, PasswordResetToken, User, UserDetails
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .decorators import nocache
from communities.models import Community
from django.db import IntegrityError
import re
from allauth.socialaccount.models import SocialAccount

def index(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about-us.html')

def contacts(request):
    return render(request, 'contact.html')

@login_required
@nocache
def admin_index(request):
    return render(request, 'user/admin_dashboard.html')
@login_required
@nocache
def community_admin_index(request):
    return render(request, 'user/community_admin_index.html')
@login_required
@nocache
def member_index(request):
    return render(request, 'user/member_index.html')

@login_required
@nocache
def user_profile(request):
    user = request.user
    user_details = user.details

    return render(request, 'user/profile.html', {'user': user, 'user_details': user_details})

@login_required
@nocache
def community_profile(request):
    user = request.user
    user_details = user.details
    return render(request, 'user/community_profile.html', {'user': user, 'user_details': user_details})

def login_page(request):
    if request.user.is_authenticated:
        user_details, created = UserDetails.objects.get_or_create(user=request.user)
        if user_details.role == "admin":
            return redirect('users:admin_index')
        profile_complete = user_details.role and user_details.phone_number and user_details.place
        if profile_complete:
            if user_details.role == "member":
                return redirect('users:member_index')
            if user_details.role == "community_admin":
                try:
                    community = Community.objects.get(admin=request.user)
                    has_community = community.name and community.description
                    if has_community:
                        return redirect('users:community_admin_index')
                    else:
                        return redirect('communities:create_community')
                except Community.DoesNotExist:
                    return redirect('communities:create_community')
        else:
            return redirect('users:select_user_type')

    return render(request, 'user/login.html')

def send_welcome_email(user):
    subject = 'Welcome to EvoCom'
    context = {'user': user}
    html_content = render_to_string('user/welcome_mail.html', context)
    text_content = strip_tags(html_content)
    send_mail(
        subject,
        text_content,
        settings.EMAIL_HOST_USER,
        [user.email],
        html_message=html_content,
        fail_silently=True,  # This ensures the email sending does not block the response
    )

def send_password_reset_email(user, token):
    reset_url = f'{settings.SITE_URL}/reset_password/{token}/'
    subject = 'Password Reset Request'
    context = {
        'user': user,
        'reset_url': reset_url,
    }
    html_content = render_to_string('user/password_reset_email.html', context)
    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [user.email])
    email.attach_alternative(html_content, 'text/html')
    email.send()

@require_POST
def register_view(request):
    username = request.POST.get('username')
    email = request.POST.get('email')
    password1 = request.POST.get('password1')
    password2 = request.POST.get('password2')

    if password1 != password2:
        return JsonResponse({'error': 'Passwords do not match'}, status=400)

    try:
        user = User.objects.create_user(username=username, email=email, password=password1)
        UserDetails.objects.create(user=user)
        send_welcome_email(user)  # Send welcome email
        messages.success(request, 'User registered successfully!')  # Add success message
        return JsonResponse({'success': 'User registered successfully', 'redirect_url': '/'})  # Redirect to home or intended page

    except IntegrityError as e:
        if 'unique constraint' in str(e).lower():
            if 'username' in str(e).lower():
                return JsonResponse({'error': 'This username is already taken'}, status=400)
            elif 'email' in str(e).lower():
                return JsonResponse({'error': 'This email is already registered'}, status=400)
        return JsonResponse({'error': 'An error occurred during registration'}, status=400)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def login_view(request):
    user = request.user 
    if request.user.is_authenticated:
        user_details, created = UserDetails.objects.get_or_create(user=request.user)
        if user_details.role == "admin":
            return redirect('users:admin_index')
        profile_complete = user_details.role and user_details.phone_number and user_details.place
        if profile_complete:
            if user_details.role == "member":
                return redirect('users:member_index')
            if user_details.role == "community_admin":
                try:
                    community = Community.objects.get(admin=user)
                    has_community = community.name and community.description
                    if has_community:
                        return redirect('users:community_admin_index')
                    else:
                        return redirect('communities:create_community')
                except Community.DoesNotExist:
                    return redirect('communities:create_community')
        else:
            return redirect('users:select_user_type')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            user_details, created = UserDetails.objects.get_or_create(user=user)
            if user_details.role == "admin":
                return redirect('users:admin_index')
            profile_complete = user_details.role and user_details.phone_number and user_details.place
            if profile_complete:
                if user_details.role == "member":
                    return redirect('users:member_index')
                if user_details.role == "community_admin":
                    try:
                        community = Community.objects.get(admin=user)
                        has_community = community.name and community.description
                        if has_community:
                            return redirect('users:community_admin_index')
                        else:
                            return redirect('communities:create_community')
                    except Community.DoesNotExist:
                        return redirect('communities:create_community')
            else:
                return redirect('users:select_user_type')
        else:
            return render(request, 'user/login.html', {'error': 'Invalid username or password.'})

    return render(request, 'user/login.html')

def user_logout(request):
    logout(request)
    return redirect('users:index')

@login_required
def select_user_type(request):
    if request.method == 'POST':
        user_details = request.user.details
        role = request.POST.get('role')
        user_details.role = role
        user_details.save()
        return redirect('users:complete_profile')

    roles = UserDetails.ROLE_CHOICES
    context = {
        'roles': roles
    }
    return render(request, 'user/select_user_type.html', context)

@login_required
def complete_profile(request):
    user = request.user
    user_details = user.details
    if request.method == 'POST':
        # Validate and update first name
        first_name = request.POST.get('first_name')
        if not first_name or len(first_name) < 2:
            messages.error(request, 'First name must be at least 2 characters long.')
            return render(request, 'user/profile_completion.html', {'user': user, 'user_details': user_details})
        user.first_name = first_name

        # Validate and update last name
        last_name = request.POST.get('last_name')
        if not last_name or len(last_name) < 1:
            messages.error(request, 'Last name must be at least 1 characters long.')
            return render(request, 'user/profile_completion.html', {'user': user, 'user_details': user_details})
        user.last_name = last_name

        # Validate and update phone number
        phone_number = request.POST.get('phone_number')
        if not re.match(r'^[6-9]\d{9}$', phone_number):
            messages.error(request, 'Please enter a valid 10-digit Indian phone number.')
            return render(request, 'user/profile_completion.html', {'user': user, 'user_details': user_details})
        user_details.phone_number = phone_number

        # Validate and update gender
        gender = request.POST.get('gender')
        if not gender:
            messages.error(request, 'Please select a gender.')
            return render(request, 'user/profile_completion.html', {'user': user, 'user_details': user_details})
        user_details.gender = gender

        # Validate and update place
        place = request.POST.get('place')
        if not place or len(place) < 2:
            messages.error(request, 'Place must be at least 2 characters long.')
            return render(request, 'user/profile_completion.html', {'user': user, 'user_details': user_details})
        user_details.place = place

        # Validate and update address
        address = request.POST.get('address')
        if not address or len(address) < 10:
            messages.error(request, 'Address must be at least 10 characters long.')
            return render(request, 'user/profile_completion.html', {'user': user, 'user_details': user_details})
        user_details.address = address

        user.save()
        user_details.save()
        messages.success(request, 'Profile completed successfully!')
        
        if user_details.role == "member":
            return redirect('users:member_index')
        if user_details.role == "community_admin":
            return redirect('communities:create_community')
        if user_details.role == "admin":
            return redirect('users:admin_index')

    return render(request, 'user/profile_completion.html', {'user': user, 'user_details': user_details})


def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            # Check if the user is a Google user
            if SocialAccount.objects.filter(user=user, provider='google').exists():
                return JsonResponse({
                    "status": "error",
                    "message": "This email is associated with a Google account. Please use Google Sign-In to access your account."
                })
            else:
                # Proceed with the normal password reset process
                token = PasswordResetToken.objects.create(user=user)
                send_password_reset_email(user, token.token)
                return JsonResponse({
                    "status": "success",
                    "message": "Password reset link has been sent to your email."
                })
        except User.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "message": "No user found with this email address."
            })
    return render(request, 'user/forgot_password.html')

def reset_password(request, token):
    reset_token = PasswordResetToken.objects.filter(token=token, expiry__gt=timezone.now()).first()
    if not reset_token:
        return HttpResponse("Invalid or expired token.")
    
    if request.method == "POST":
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if password1 == password2:
            reset_token.user.set_password(password1)
            reset_token.user.save()
            reset_token.delete()
            return HttpResponse("Your password has been reset successfully.")
        else:
            return HttpResponse("Passwords do not match.")
    
    return render(request, 'user/reset_password.html', {'token': token})

@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        user_details = user.details

        # Validate and update first name
        first_name = request.POST.get('first_name')
        if not first_name or len(first_name) < 2:
            messages.error(request, 'First name must be at least 2 characters long.')
            return redirect('users:user_profile')
        user.first_name = first_name

        # Validate and update last name
        last_name = request.POST.get('last_name')
        if not last_name or len(last_name) < 1:
            messages.error(request, 'Last name must be at least 1 characters long.')
            return redirect('users:user_profile')
        user.last_name = last_name

        # Validate and update phone number
        phone_number = request.POST.get('phone_number')
        if not re.match(r'^[6-9]\d{9}$', phone_number):
            messages.error(request, 'Please enter a valid 10-digit Indian phone number.')
            return redirect('users:user_profile')
        user_details.phone_number = phone_number

        # Validate and update place
        place = request.POST.get('place')
        if not place or len(place) < 2:
            messages.error(request, 'Place must be at least 2 characters long.')
            return redirect('users:user_profile')
        user_details.place = place

        # Validate and update address
        address = request.POST.get('address')
        if not address or len(address) < 10:
            messages.error(request, 'Address must be at least 10 characters long.')
            return redirect('users:user_profile')
        user_details.address = address

        user.save()
        user_details.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('users:user_profile')

    context = {
        'user': request.user,
        'is_google_user': request.user.is_google_user
    }
    return render(request, 'user/profile.html', context)

@login_required
def community_update_profile(request):
    if request.method == 'POST':
        user = request.user
        user_details = user.details

        # Validate and update first name
        first_name = request.POST.get('first_name')
        if not first_name or len(first_name) < 2:
            messages.error(request, 'First name must be at least 2 characters long.')
            return redirect('users:community_profile')
        user.first_name = first_name

        # Validate and update last name
        last_name = request.POST.get('last_name')
        if not last_name or len(last_name) < 1:
            messages.error(request, 'Last name must be at least 1 characters long.')
            return redirect('users:community_profile')
        user.last_name = last_name

        # Validate and update phone number
        phone_number = request.POST.get('phone_number')
        if not re.match(r'^[6-9]\d{9}$', phone_number):
            messages.error(request, 'Please enter a valid 10-digit Indian phone number.')
            return redirect('users:community_profile')
        user_details.phone_number = phone_number

        # Validate and update place
        place = request.POST.get('place')
        if not place or len(place) < 2:
            messages.error(request, 'Place must be at least 2 characters long.')
            return redirect('users:community_profile')
        user_details.place = place

        # Validate and update address
        address = request.POST.get('address')
        if not address or len(address) < 10:
            messages.error(request, 'Address must be at least 10 characters long.')
            return redirect('users:community_profile')
        user_details.address = address

        user.save()
        user_details.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('users:community_profile')

    context = {
        'user': request.user,
        'is_google_user': request.user.is_google_user
    }
    return render(request, 'user/community_profile.html', context)

@login_required
def password_change(request):
    if request.method == 'POST':
        user = request.user
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not user.check_password(current_password):
            return JsonResponse({'error': 'Current password is incorrect'}, status=400)
        
        if new_password != confirm_password:
            return JsonResponse({'error': 'New passwords do not match'}, status=400)
        
        if len(new_password) < 8:
            return JsonResponse({'error': 'Password must be at least 8 characters long'}, status=400)
        
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)  # Important for keeping the user logged in
        return JsonResponse({'success': 'Password has been changed successfully'})
    return render(request, 'user/password_change.html')

@login_required
def community_password_change(request):
    if request.method == 'POST':
        user = request.user
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not user.check_password(current_password):
            return JsonResponse({'error': 'Current password is incorrect'}, status=400)
        
        if new_password != confirm_password:
            return JsonResponse({'error': 'New passwords do not match'}, status=400)
        
        if len(new_password) < 8:
            return JsonResponse({'error': 'Password must be at least 8 characters long'}, status=400)
        
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)  # Important for keeping the user logged in
        return JsonResponse({'success': 'Password has been changed successfully'})
    return render(request, 'user/community_password_change.html')
@login_required
def password_change(request):
    if request.method == 'POST':
        user = request.user
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not user.check_password(current_password):
            return JsonResponse({'error': 'Current password is incorrect'}, status=400)
        
        if new_password != confirm_password:
            return JsonResponse({'error': 'New passwords do not match'}, status=400)
        
        if len(new_password) < 8:
            return JsonResponse({'error': 'Password must be at least 8 characters long'}, status=400)
        
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)  # Important for keeping the user logged in
        return JsonResponse({'success': 'Password has been changed successfully'})
    return render(request, 'user/password_change.html')

@require_POST
def check_email(request):
    email = request.POST.get('email')
    exists = User.objects.filter(email=email).exists()
    return JsonResponse({'exists': exists})

@require_POST
def check_username(request):
    username = request.POST.get('username')
    exists = User.objects.filter(username=username).exists()
    return JsonResponse({'exists': exists})

@login_required
def request_organizer(request):
    if request.method == "POST":
        community_id = request.POST.get('community')
        community = get_object_or_404(Community, id=community_id)
        EventOrganizerRequest.objects.create(
            member=request.user,
            community=community,
            status='pending'
        )
        return redirect('communities:view_community', pk=community.id)  # Redirect to a relevant page


@login_required
def admin_organizer_requests(request):
    if not request.user.is_staff:  # Adjust this check as needed
        return redirect('home')  # Redirect to a relevant page

    requests = EventOrganizerRequest.objects.filter(status='pending')
    return render(request, 'events/admin_organizer_requests.html', {'requests': requests})

@login_required
def approve_organizer_request(request, request_id):
    if not request.user.is_staff:  # Adjust this check as needed
        return redirect('home')  # Redirect to a relevant page

    organizer_request = get_object_or_404(EventOrganizerRequest, id=request_id)
    organizer_request.status = 'approved'
    organizer_request.save()
    # Create EventOrganizer entry here if needed
    return redirect('events:admin_organizer_requests')

@login_required
def reject_organizer_request(request, request_id):
    if not request.user.is_staff:  # Adjust this check as needed
        return redirect('home')  # Redirect to a relevant page

    organizer_request = get_object_or_404(EventOrganizerRequest, id=request_id)
    organizer_request.status = 'rejected'
    organizer_request.save()
    return redirect('events:admin_organizer_requests')

def google_login_callback(request):
    # ... existing code ...
    user = request.user
    if SocialAccount.objects.filter(user=user, provider='google').exists():
        user.is_google_user = True
        user.save()
    # ... rest of the code ...
