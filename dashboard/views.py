from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField

from bookings.models import Booking, BookingServiceItem
from leads.models import Lead
from invoices.models import Invoice


@login_required
def index(request):
    """
    Render the dashboard index page
    Requires user to be logged in and have a business
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    # Get business data
    business = request.user.business
    
    # Get today's date and date ranges
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    last_week_start = week_start - timedelta(days=7)
    last_week_end = week_start - timedelta(days=1)
    
    # Get upcoming appointments (today and future)
    upcoming_appointments = Booking.objects.filter(
        business=business,
        booking_date__gte=today
    ).order_by('booking_date', 'start_time')[:5]
    
    # Get today's appointments count
    todays_appointments_count = Booking.objects.filter(
        business=business,
        created_at__date=today
    ).count()

    
    # Get yesterday's appointments count for comparison
    yesterday = today - timedelta(days=1)
    yesterdays_appointments_count = Booking.objects.filter(
        business=business,
        created_at__date=yesterday
    ).count()
    
    # Calculate appointment change percentage
    if yesterdays_appointments_count > 0:
        appointment_change_percent = int((todays_appointments_count - yesterdays_appointments_count) / yesterdays_appointments_count * 100)
    else:
        appointment_change_percent = 100 if todays_appointments_count > 0 else 0
    
    # Get new leads (last 7 days)
    new_leads = Lead.objects.filter(
        business=business,
        created_at__gte=today - timedelta(days=7)
    ).order_by('-created_at')[:5]
    
    # Get new leads count this week
    new_leads_count = Lead.objects.filter(
        business=business,
        created_at__date__range=[week_start, week_end]
    ).count()
    
    # Get new leads count last week for comparison
    last_week_leads_count = Lead.objects.filter(
        business=business,
        created_at__date__range=[last_week_start, last_week_end]
    ).count()
    
    # Calculate lead change percentage
    if last_week_leads_count > 0:
        lead_change_percent = int((new_leads_count - last_week_leads_count) / last_week_leads_count * 100)
    else:
        lead_change_percent = 100 if new_leads_count > 0 else 0
    
    # Get AI calls count (placeholder - would be replaced with actual data)
    ai_calls_count = 24
    ai_calls_change_percent = 15
    
    # Get revenue this week from booking service items
    revenue_this_week = BookingServiceItem.objects.filter(
        booking__business=business,
        booking__created_at__date__range=[week_start, week_end]
    ).annotate(
        item_total=ExpressionWrapper(
            F('price_at_booking') * F('quantity'),
            output_field=DecimalField()
        )
    ).aggregate(total=Sum('item_total'))['total'] or 0
    
    # Get revenue last week for comparison
    revenue_last_week = BookingServiceItem.objects.filter(
        booking__business=business,
        booking__created_at__date__range=[last_week_start, last_week_end]
    ).annotate(
        item_total=ExpressionWrapper(
            F('price_at_booking') * F('quantity'),
            output_field=DecimalField()
        )
    ).aggregate(total=Sum('item_total'))['total'] or 0
    
    # Calculate revenue change percentage
    if revenue_last_week > 0:
        revenue_change_percent = int((revenue_this_week - revenue_last_week) / revenue_last_week * 100)
    else:
        revenue_change_percent = 100 if revenue_this_week > 0 else 0
    
    context = {
        'business': business,
        'upcoming_appointments': upcoming_appointments,
        'todays_appointments_count': todays_appointments_count,
        'appointment_change_percent': appointment_change_percent,
        'new_leads': new_leads,
        'new_leads_count': new_leads_count,
        'lead_change_percent': lead_change_percent,
        'ai_calls_count': ai_calls_count,
        'ai_calls_change_percent': ai_calls_change_percent,
        'revenue_this_week': revenue_this_week,
        'revenue_change_percent': revenue_change_percent,
        'today': today,
    }
    

    return render(request, 'dashboard/index.html', context)
