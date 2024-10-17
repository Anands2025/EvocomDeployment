from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse
from communities.models import Community, CommunityCategory, CommunityTags
from events.models import EventCategory, Event

User = get_user_model()

def admin_check(user):
    user_details = user.details
    return user_details.role == "admin"

@user_passes_test(admin_check)
def user_list(request):
    users = User.objects.all()
    return render(request, 'evocom_admin/user_list.html', {'users': users})

@user_passes_test(admin_check)
def community_list(request):
    communities = Community.objects.all()
    return render(request, 'evocom_admin/community_list.html', {'communities': communities})

@user_passes_test(admin_check)
def category_list(request):
    categories = CommunityCategory.objects.all()
    return render(request, 'evocom_admin/category_list.html', {'categories': categories})

@user_passes_test(admin_check)
def category_add(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        if CommunityCategory.objects.filter(name__iexact=name).exists():
            return JsonResponse({
                'status': 'error',
                'message': f"A community category with the name '{name}' already exists."
            })
        
        CommunityCategory.objects.create(name=name, description=description, status="enabled")
        return JsonResponse({
            'status': 'success',
            'message': f"Community category '{name}' has been successfully added."
        })
    
    return render(request, 'evocom_admin/category_form.html')

@user_passes_test(admin_check)
def category_edit(request, category_id):
    category = get_object_or_404(CommunityCategory, id=category_id)
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.description = request.POST.get('description')
        category.save()
        return redirect('evocom_admin:category_list')
    return render(request, 'evocom_admin/category_form.html', {'category': category})

@user_passes_test(admin_check)
def category_delete(request, category_id):
    category = CommunityCategory.objects.get(id=category_id)
    category.status="disabled"
    category.save()
    return redirect('evocom_admin:category_list')

@user_passes_test(admin_check)
def category_enable(request, category_id):
    category = CommunityCategory.objects.get(id=category_id)
    category.status="enabled"
    category.save()
    return redirect('evocom_admin:category_list')

@user_passes_test(admin_check)
def tag_list(request):
    tags = CommunityTags.objects.all()
    return render(request, 'evocom_admin/tag_list.html', {'tags': tags})

@user_passes_test(admin_check)
def tag_add(request):
    if request.method == 'POST':
        tag_name = request.POST.get('tag_name')
        tag_description = request.POST.get('tag_description')
        CommunityTags.objects.create(tag_name=tag_name, tag_description=tag_description)
        return redirect('evocom_admin:tag_list')
    return render(request, 'evocom_admin/tag_form.html')

@user_passes_test(admin_check)
def tag_edit(request, tag_id):
    tag = get_object_or_404(CommunityTags, id=tag_id)
    if request.method == 'POST':
        tag.tag_name = request.POST.get('tag_name')
        tag.tag_description = request.POST.get('tag_description')
        tag.save()
        return redirect('evocom_admin:tag_list')
    return render(request, 'evocom_admin/tag_form.html', {'tag': tag})

@user_passes_test(admin_check)
def event_category_list(request):
    event_categories = EventCategory.objects.all()
    return render(request, 'evocom_admin/event_category_list.html', {'event_categories': event_categories})

@user_passes_test(admin_check)
def event_category_add(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        if EventCategory.objects.filter(name__iexact=name).exists():
            return JsonResponse({
                'status': 'error',
                'message': f"An event category with the name '{name}' already exists."
            })
        
        EventCategory.objects.create(name=name, description=description, status="enabled")
        return JsonResponse({
            'status': 'success',
            'message': f"Event category '{name}' has been successfully added."
        })
    
    return render(request, 'evocom_admin/event_category_form.html')

@user_passes_test(admin_check)
def event_category_edit(request, category_id):
    category = get_object_or_404(EventCategory, id=category_id)
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.description = request.POST.get('description')
        category.save()
        return redirect('evocom_admin:event_category_list')
    return render(request, 'evocom_admin/event_category_form.html', {'category': category})

@user_passes_test(admin_check)
def event_category_delete(request, category_id):
    category = EventCategory.objects.get(id=category_id)
    category.status="disabled"
    category.save()
    return redirect('evocom_admin:event_category_list')

@user_passes_test(admin_check)
def event_category_enable(request, category_id):
    category = EventCategory.objects.get(id=category_id)
    category.status="enabled"
    category.save()
    return redirect('evocom_admin:event_category_list')

def event_list(request):
    events = Event.objects.all().select_related('category', 'community').order_by('-start_datetime')
    return render(request, 'evocom_admin/events_list.html', {'events': events})