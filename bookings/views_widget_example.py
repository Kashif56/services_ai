"""
View for rendering the widget example page
"""
from django.shortcuts import render
from business.models import Business


def widget_example(request):
    """
    Render the widget example page
    Shows how to embed the booking widget
    """
    # Get the first active business as an example
    # In production, you would pass the specific business ID
    business = Business.objects.filter(is_active=True).first()
    
    context = {
        'business_id': business.id if business else 'your-business-id',
    }
    
    return render(request, 'bookings/widget_example.html', context)
