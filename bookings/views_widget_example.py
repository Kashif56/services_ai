"""
View for rendering the widget example page
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from business.models import Business



@login_required
def widget_showcase(request):
    """
    Render the widget showcase page for logged-in users
    Shows embedding instructions and features
    """
    business = getattr(request.user, 'business', None)
    
    if not business:
        business = Business.objects.filter(is_active=True).first()
    
    context = {
        'business': business,
    }
    
    return render(request, 'bookings/widget_showcase.html', context)
