from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import StaffProfile
from bookings.models import BookingStaffAssignment, Booking
from datetime import datetime, timedelta


@login_required
def staff_dashboard(request):
    """
    Staff dashboard - redirects to their staff detail page
    """
    try:
        staff_profile = request.user.staff_profile
        return redirect('business:staff_detail', staff_id=staff_profile.staff_member.id)
    except StaffProfile.DoesNotExist:
        messages.error(request, "Staff profile not found. Please contact your administrator.")
        return redirect('accounts:login')


@login_required
def staff_bookings(request):
    """
    View all bookings assigned to the logged-in staff member
    """
    try:
        staff_profile = request.user.staff_profile
        staff_member = staff_profile.staff_member
        
        # Get all bookings assigned to this staff member
        assigned_bookings = BookingStaffAssignment.objects.filter(
            staff_member=staff_member
        ).select_related('booking', 'booking__lead', 'booking__service_offering').order_by('-booking__booking_date', '-booking__start_time')
        
        # Filter by status if provided
        status_filter = request.GET.get('status')
        if status_filter:
            assigned_bookings = assigned_bookings.filter(booking__status=status_filter)
        
        # Filter by date range
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        if date_from:
            assigned_bookings = assigned_bookings.filter(booking__booking_date__gte=date_from)
        if date_to:
            assigned_bookings = assigned_bookings.filter(booking__booking_date__lte=date_to)
        
        context = {
            'staff_profile': staff_profile,
            'assigned_bookings': assigned_bookings,
            'status_filter': status_filter,
            'date_from': date_from,
            'date_to': date_to,
        }
        
        return render(request, 'staff/bookings.html', context)
        
    except StaffProfile.DoesNotExist:
        messages.error(request, "Staff profile not found. Please contact your administrator.")
        return redirect('accounts:login')
