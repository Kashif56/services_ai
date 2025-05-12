from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.core.paginator import Paginator

from .models import Notification

@login_required
def notification_list(request):
    """Display all notifications for the current user"""
    notifications = Notification.objects.filter(user=request.user)
    paginator = Paginator(notifications, 20)  # Show 20 notifications per page
    
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'notifications/notification_list.html', {
        'page_obj': page_obj,
    })

@login_required
@require_POST
def mark_as_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_read()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('notifications:notification_list')

@login_required
@require_POST
def mark_all_as_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('notifications:notification_list')

@login_required
def get_notifications(request):
    """Get notifications for the dropdown in the navbar"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    html = render_to_string('notifications/notification_dropdown.html', {
        'notifications': notifications,
    }, request=request)
    
    return JsonResponse({
        'html': html,
        'unread_count': unread_count
    })
