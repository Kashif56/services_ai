from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib import messages
import json
from .utils import get_user_business

from bookings.models import StaffMember, StaffRole, StaffAvailability, WEEKDAY_CHOICES, AVAILABILITY_TYPE




# Staff Management Views
@login_required
def staff_management(request):
    """
    Render the staff management page
    Shows all staff members for the business
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        messages.warning(request, 'No business associated with your account.')
        return redirect('accounts:login')
    
    # Get all staff members for this business
    staff_members = StaffMember.objects.filter(business=business)
    staff_roles = StaffRole.objects.filter(business=business, is_active=True)
    
    context = {
        'business': business,
        'staff_members': staff_members,
        'staff_roles': staff_roles,
    }
    
    return render(request, 'business/staff.html', context)

@login_required
@require_http_methods(["POST"])
def add_staff(request):
    """
    Add a new staff member
    Handles form submission from the staff management page
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        messages.warning(request, 'No business associated with your account.')
        return redirect('accounts:login')
    
    try:
        from bookings.models import StaffMember, StaffRole, StaffAvailability, AVAILABILITY_TYPE, WEEKDAY_CHOICES
        from datetime import time
        
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone', '')
        bio = request.POST.get('bio', '')
        is_active = 'is_active' in request.POST
        
        # Validate required fields
        if not first_name or not last_name or not email:
            messages.error(request, 'First name, last name, and email are required.')
            return redirect('business:staff')
        
        # Create staff member
        staff = StaffMember.objects.create(
            business=business,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            bio=bio,
            is_active=is_active
        )
        
        # Handle profile image if provided
        if 'profile_image' in request.FILES:
            staff.profile_image = request.FILES['profile_image']
            staff.save()
        
        # Add roles
        role_ids = request.POST.getlist('roles')
        if role_ids:
            roles = StaffRole.objects.filter(id__in=role_ids, business=business)
            staff.roles.set(roles)
        
        # Create default weekly availabilities (9am-5pm, Monday-Friday)
        for day_num, _ in WEEKDAY_CHOICES.choices:
            # Skip weekends (5=Saturday, 6=Sunday)
            is_weekend = day_num in [5, 6]
            
            StaffAvailability.objects.create(
                staff_member=staff,
                availability_type=AVAILABILITY_TYPE.WEEKLY,
                weekday=day_num,
                start_time=time(9, 0),  # 9:00 AM
                end_time=time(17, 0),   # 5:00 PM
                off_day=is_weekend      # Mark weekends as off by default
            )
        
        messages.success(request, f'Staff member {staff.get_full_name()} added successfully with default availability schedule!')
    except Exception as e:
        messages.error(request, f'Error adding staff member: {str(e)}')
    
    return redirect('business:staff')

@login_required
def staff_detail(request, staff_id):
    """
    Render the staff detail page
    Shows staff information, availability, and assigned bookings
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        business = request.user.staff_profile.business
    else:
        business = request.user.business
        
    from datetime import datetime, timedelta
    
    # Get week offset from query parameter (default to current week)
    week_offset = int(request.GET.get('week_offset', 0))
    
    # Calculate the week's start date (Monday)
    today = datetime.now().date()
    current_week_start = today - timedelta(days=today.weekday())
    week_start = current_week_start + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)
    
    # Get staff member, ensuring it belongs to this business
    staff = get_object_or_404(StaffMember, id=staff_id, business=business)
    
    # Get all roles for this business
    all_roles = StaffRole.objects.filter(business=business, is_active=True)
    
    # Get staff availability
    weekly_availabilities = StaffAvailability.objects.filter(
        staff_member=staff,
        availability_type=AVAILABILITY_TYPE.WEEKLY
    ).order_by('weekday', 'start_time')
    
    # Specific dates are ONLY for holidays/off days
    specific_off_days = StaffAvailability.objects.filter(
        staff_member=staff,
        availability_type=AVAILABILITY_TYPE.SPECIFIC,
        off_day=True
    ).order_by('specific_date')
    
    # Get holidays for the current week
    week_holidays = specific_off_days.filter(
        specific_date__gte=week_start,
        specific_date__lte=week_end
    )
    
    # Build week calendar data
    week_calendar = []
    for day_offset in range(7):
        current_date = week_start + timedelta(days=day_offset)
        weekday_num = current_date.weekday()
        
        # Get availability for this weekday
        day_availabilities = weekly_availabilities.filter(weekday=weekday_num)
        
        # Check if this specific date is a holiday
        is_holiday = week_holidays.filter(specific_date=current_date).exists()
        holiday_reason = None
        if is_holiday:
            holiday = week_holidays.filter(specific_date=current_date).first()
            holiday_reason = holiday.notes if holiday else None
        
        # Determine if it's an off day (either weekly off or holiday)
        is_off_day = False
        time_ranges = []
        
        if is_holiday:
            is_off_day = True
        elif day_availabilities.exists():
            for avail in day_availabilities:
                if avail.off_day:
                    is_off_day = True
                else:
                    time_ranges.append({
                        'start': avail.start_time,
                        'end': avail.end_time
                    })
        
        week_calendar.append({
            'date': current_date,
            'weekday': WEEKDAY_CHOICES(weekday_num).label,
            'is_today': current_date == today,
            'is_off_day': is_off_day,
            'is_holiday': is_holiday,
            'holiday_reason': holiday_reason,
            'time_ranges': time_ranges
        })
    
    # Get weekly off days (days with no availability set)
    weekly_off_days = []
    for avail in weekly_availabilities:
        if avail.off_day and avail.weekday not in weekly_off_days:
            weekly_off_days.append(avail.weekday)
    
    # Get assigned bookings
    from bookings.models import BookingStaffAssignment, StaffServiceAssignment
    from business.models import ServiceOffering
    assigned_bookings = BookingStaffAssignment.objects.filter(
        staff_member=staff
    ).select_related('booking', 'booking__lead', 'booking__service_offering').order_by('-booking__start_time')

    # Get service assignments
    service_assignments = StaffServiceAssignment.objects.filter(
        staff_member=staff
    ).select_related('service_offering').order_by('-is_primary', 'service_offering__name')
    
    # Get available services for the business
    available_services = ServiceOffering.objects.filter(
        business=business,
        is_active=True
    ).order_by('name')
    
    context = {
        'business': business,
        'staff': staff,
        'all_roles': all_roles,
        'weekly_availabilities': weekly_availabilities,
        'specific_off_days': specific_off_days,
        'weekly_off_days': weekly_off_days,
        'assigned_bookings': assigned_bookings,
        'service_assignments': service_assignments,
        'available_services': available_services,
        'weekday_choices': WEEKDAY_CHOICES.choices,
        'week_calendar': week_calendar,
        'week_start': week_start,
        'week_end': week_end,
        'week_offset': week_offset,
    }
    
    return render(request, 'business/staff_detail.html', context)

@login_required
@require_http_methods(["POST"])
def update_staff(request, staff_id):
    """
    Update staff member information
    Handles form submission from the staff detail page
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        messages.warning(request, 'No business associated with your account.')
        return redirect('accounts:login')
    
    from bookings.models import StaffMember, StaffRole
    
    # Get staff member, ensuring it belongs to this business
    staff = get_object_or_404(StaffMember, id=staff_id, business=business)
    
    try:
        # Update staff information
        staff.first_name = request.POST.get('first_name')
        staff.last_name = request.POST.get('last_name')
        staff.email = request.POST.get('email')
        staff.phone = request.POST.get('phone', '')
        staff.bio = request.POST.get('bio', '')
        staff.is_active = 'is_active' in request.POST
        
        # Handle profile image if provided
        if 'profile_image' in request.FILES:
            staff.profile_image = request.FILES['profile_image']
        
        staff.save()
        
        # Update roles
        role_ids = request.POST.getlist('roles')
        if role_ids:
            roles = StaffRole.objects.filter(id__in=role_ids, business=business)
            staff.roles.set(roles)
        else:
            staff.roles.clear()
        
        messages.success(request, f'Staff member {staff.get_full_name()} updated successfully!')
    except Exception as e:
        messages.error(request, f'Error updating staff member: {str(e)}')
    
    return redirect('business:staff_detail', staff_id=staff_id)

@login_required
@require_http_methods(["POST"])
def update_staff_status(request):
    """
    Update staff member active status via AJAX
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        return JsonResponse({
            'success': False,
            'message': 'No business associated with your account.'
        })
    
    try:
        # Parse JSON data from request body
        data = json.loads(request.body)
        staff_id = data.get('staff_id')
        is_active = data.get('is_active')
        
        from bookings.models import StaffMember
        
        # Get staff member, ensuring it belongs to this business
        staff = get_object_or_404(StaffMember, id=staff_id, business=business)
        
        # Update status
        staff.is_active = is_active
        staff.save(update_fields=['is_active', 'updated_at'])
        
        return JsonResponse({
            'success': True,
            'message': f'Staff status updated successfully!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

@login_required
@require_http_methods(["POST"])
def add_staff_availability(request, staff_id):
    """
    Add new availability for a staff member
    Handles form submission from the staff detail page
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        messages.warning(request, 'No business associated with your account.')
        return redirect('accounts:login')
    
    from bookings.models import StaffMember, StaffAvailability, AVAILABILITY_TYPE
    from django.utils.dateparse import parse_time, parse_date
    
    # Get staff member, ensuring it belongs to this business
    staff = get_object_or_404(StaffMember, id=staff_id, business=business)
    
    try:
        # Get form data
        availability_type = request.POST.get('availability_type')
        off_day = 'off_day' in request.POST
        
        # For specific dates, ALWAYS mark as off_day (holidays only)
        if availability_type == 'specific':
            off_day = True
            # Holidays are full day, so use midnight to end of day
            from datetime import time
            start_time = time(0, 0)
            end_time = time(23, 59)
        else:
            # For weekly schedules, get the times from form
            start_time = parse_time(request.POST.get('start_time'))
            end_time = parse_time(request.POST.get('end_time'))
        
        # Create availability based on type
        if availability_type == 'weekly':
            weekday = int(request.POST.get('weekday'))
            
            # Check if an availability already exists for this weekday and is not an off day
            existing_availabilities = StaffAvailability.objects.filter(
                staff_member=staff,
                availability_type=AVAILABILITY_TYPE.WEEKLY,
                weekday=weekday
            )
            
            if existing_availabilities.exists() and not off_day:
                messages.warning(request, f'An availability for this weekday already exists. Please edit the existing one instead.')
                return redirect('business:staff_detail', staff_id=staff_id)
            
            # If it's an off day, we can have multiple (or replace existing)
            if off_day:
                # If marking as off day, remove any existing availabilities for this day
                existing_availabilities.delete()
            
            StaffAvailability.objects.create(
                staff_member=staff,
                availability_type=AVAILABILITY_TYPE.WEEKLY,
                weekday=weekday,
                start_time=start_time,
                end_time=end_time,
                off_day=off_day
            )
            
            messages.success(request, 'Weekly availability added successfully!')
        elif availability_type == 'specific':
            from_date = parse_date(request.POST.get('from_date'))
            to_date = parse_date(request.POST.get('to_date'))
            notes = request.POST.get('notes', '')
            
            if not from_date or not to_date:
                messages.error(request, 'Both from and to dates are required.')
                return redirect('business:staff_detail', staff_id=staff_id)
            
            if to_date < from_date:
                messages.error(request, 'To date must be after or equal to from date.')
                return redirect('business:staff_detail', staff_id=staff_id)
            
            # Create holidays for each date in the range
            from datetime import timedelta as td
            current_date = from_date
            created_count = 0
            skipped_count = 0
            
            while current_date <= to_date:
                # Check if a holiday already exists for this date
                existing_off_days = StaffAvailability.objects.filter(
                    staff_member=staff,
                    availability_type=AVAILABILITY_TYPE.SPECIFIC,
                    specific_date=current_date,
                    off_day=True
                )
                
                if not existing_off_days.exists():
                    # Create holiday (specific dates are ONLY for marking days off)
                    StaffAvailability.objects.create(
                        staff_member=staff,
                        availability_type=AVAILABILITY_TYPE.SPECIFIC,
                        specific_date=current_date,
                        start_time=start_time,
                        end_time=end_time,
                        off_day=True,  # Always True for specific dates
                        notes=notes
                    )
                    created_count += 1
                else:
                    skipped_count += 1
                
                current_date += td(days=1)
            
            if created_count > 0:
                if created_count == 1:
                    messages.success(request, 'Holiday added successfully!')
                else:
                    messages.success(request, f'{created_count} holidays added successfully!')
            
            if skipped_count > 0:
                messages.info(request, f'{skipped_count} date(s) were already marked as holidays and were skipped.')
        else:
            messages.error(request, 'Invalid availability type.')
    except Exception as e:
        messages.error(request, f'Error adding availability: {str(e)}')
    
    return redirect('business:staff_detail', staff_id=staff_id)

@login_required
@require_http_methods(["POST"])
def update_staff_availability(request, staff_id):
    """
    Update an existing staff availability
    Handles form submission from the staff detail page
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        messages.warning(request, 'No business associated with your account.')
        return redirect('accounts:login')
    
    from bookings.models import StaffMember, StaffAvailability
    from django.utils.dateparse import parse_time, parse_date
    
    # Get staff member, ensuring it belongs to this business
    staff = get_object_or_404(StaffMember, id=staff_id, business=business)
    
    try:
        # Get form data
        availability_id = request.POST.get('availability_id')
        
        # Get the availability with select_related to ensure staff_member is loaded
        availability = get_object_or_404(
            StaffAvailability.objects.select_related('staff_member'), 
            id=availability_id, 
            staff_member=staff
        )
        
        # Build update dict based on availability type
        update_data = {}
        
        if availability.availability_type == 'specific':
            # For holidays, only update date and notes
            if 'specific_date' in request.POST:
                specific_date = parse_date(request.POST.get('specific_date'))
                update_data['specific_date'] = specific_date
            
            if 'notes' in request.POST:
                update_data['notes'] = request.POST.get('notes', '')
        else:
            # For weekly schedules, update times and off_day status
            start_time_str = request.POST.get('start_time')
            end_time_str = request.POST.get('end_time')
            off_day = 'off_day' in request.POST
            
            # Parse times
            start_time = parse_time(start_time_str)
            end_time = parse_time(end_time_str)
            
            update_data = {
                'start_time': start_time,
                'end_time': end_time,
                'off_day': off_day
            }
        
        # Use queryset update to bypass model validation
        if update_data:
            StaffAvailability.objects.filter(id=availability_id).update(**update_data)
            messages.success(request, 'Availability updated successfully!')
        else:
            messages.warning(request, 'No changes to update.')
    except Exception as e:
        messages.error(request, f'Error updating availability: {str(e)}')
    
    return redirect('business:staff_detail', staff_id=staff_id)

@login_required
@require_http_methods(["POST"])
def delete_staff_availability(request):
    """
    Delete staff availability via AJAX
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        return JsonResponse({
            'success': False,
            'message': 'No business associated with your account.'
        })
    
    try:
        # Parse JSON data from request body
        data = json.loads(request.body)
        availability_id = data.get('availability_id')
        
        from bookings.models import StaffAvailability
        
        # Get availability, ensuring it belongs to this business
        availability = get_object_or_404(StaffAvailability, id=availability_id, staff_member__business=business)
        
        # Delete availability
        availability.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Availability deleted successfully!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

@login_required
@require_http_methods(["POST"])
def add_staff_off_day(request, staff_id):
    """
    Add a specific off day for a staff member
    Handles form submission from the staff detail page
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        messages.warning(request, 'No business associated with your account.')
        return redirect('accounts:login')
    
    from bookings.models import StaffMember, StaffAvailability, AVAILABILITY_TYPE
    from django.utils.dateparse import parse_date
    from datetime import time
    
    # Get staff member, ensuring it belongs to this business
    staff = get_object_or_404(StaffMember, id=staff_id, business=business)
    
    try:
        # Get form data
        off_day_date = parse_date(request.POST.get('off_day_date'))
        reason = request.POST.get('reason', '')
        
        # Create off day availability
        StaffAvailability.objects.create(
            staff_member=staff,
            availability_type=AVAILABILITY_TYPE.SPECIFIC,
            specific_date=off_day_date,
            start_time=time(0, 0),  # Midnight
            end_time=time(23, 59),  # End of day
            off_day=True,
            notes=reason
        )
        
        messages.success(request, 'Off day added successfully!')
    except Exception as e:
        messages.error(request, f'Error adding off day: {str(e)}')
    
    return redirect('business:staff_detail', staff_id=staff_id)

@login_required
@require_http_methods(["POST"])
def update_weekly_off_days(request, staff_id):
    """
    Update weekly off days for a staff member
    Handles form submission from the staff detail page
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        messages.warning(request, 'No business associated with your account.')
        return redirect('accounts:login')
    
    from bookings.models import StaffMember, StaffAvailability, AVAILABILITY_TYPE
    
    # Get staff member, ensuring it belongs to this business
    staff = get_object_or_404(StaffMember, id=staff_id, business=business)
    
    try:
        # Get selected off days
        selected_off_days = [int(day) for day in request.POST.getlist('weekly_off_days')]
        
        # Delete existing weekly off days
        StaffAvailability.objects.filter(
            staff_member=staff,
            availability_type=AVAILABILITY_TYPE.WEEKLY,
            off_day=True
        ).delete()
        
        # Create new weekly off days
        for day in selected_off_days:
            StaffAvailability.objects.create(
                staff_member=staff,
                availability_type=AVAILABILITY_TYPE.WEEKLY,
                weekday=day,
                start_time=time(0, 0),  # Midnight
                end_time=time(23, 59),  # End of day
                off_day=True
            )
        
        messages.success(request, 'Weekly off days updated successfully!')
    except Exception as e:
        messages.error(request, f'Error updating weekly off days: {str(e)}')
    
    return redirect('business:staff_detail', staff_id=staff_id)

# Staff Role Management Views
@login_required
@require_http_methods(["POST"])
def add_staff_role(request):
    """
    Add a new staff role
    Handles form submission from the staff management page
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        messages.warning(request, 'No business associated with your account.')
        return redirect('accounts:login')
    
    try:
        from bookings.models import StaffRole
        
        # Get form data
        role_name = request.POST.get('role_name')
        role_description = request.POST.get('role_description', '')
        
        # Validate required fields
        if not role_name:
            messages.error(request, 'Role name is required.')
            return redirect('business:staff')
        
        # Create staff role
        StaffRole.objects.create(
            business=business,
            name=role_name,
            description=role_description,
            is_active=True
        )
        
        messages.success(request, f'Staff role "{role_name}" added successfully!')
    except Exception as e:
        messages.error(request, f'Error adding staff role: {str(e)}')
    
    return redirect('business:staff')

@login_required
@require_http_methods(["POST"])
def update_staff_role(request):
    """
    Update an existing staff role
    Handles form submission from the staff management page
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        messages.warning(request, 'No business associated with your account.')
        return redirect('accounts:login')
    
    try:
        from bookings.models import StaffRole
        
        # Get form data
        role_id = request.POST.get('role_id')
        role_name = request.POST.get('role_name')
        role_description = request.POST.get('role_description', '')
        is_active = 'is_active' in request.POST
        
        # Validate required fields
        if not role_id or not role_name:
            messages.error(request, 'Role ID and name are required.')
            return redirect('business:staff')
        
        # Get role, ensuring it belongs to this business
        role = get_object_or_404(StaffRole, id=role_id, business=business)
        
        # Update role
        role.name = role_name
        role.description = role_description
        role.is_active = is_active
        role.save()
        
        messages.success(request, f'Staff role "{role_name}" updated successfully!')
    except Exception as e:
        messages.error(request, f'Error updating staff role: {str(e)}')
    
    return redirect('business:staff')

@login_required
@require_http_methods(["POST"])
def add_service_assignment(request, staff_id):
    """
    Add a service assignment to a staff member
    Handles form submission from the staff detail page
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        messages.warning(request, 'No business associated with your account.')
        return redirect('accounts:login')
    
    from bookings.models import StaffMember, StaffServiceAssignment
    from business.models import ServiceOffering
    
    # Get staff member, ensuring it belongs to this business
    staff = get_object_or_404(StaffMember, id=staff_id, business=business)
    
    try:
        # Get form data
        service_offering_id = request.POST.get('service_offering')
        is_primary = 'is_primary' in request.POST
        
        # Validate required fields
        if not service_offering_id:
            messages.error(request, 'Service is required.')
            return redirect('business:staff_detail', staff_id=staff_id)
        
        # Get service offering, ensuring it belongs to this business
        service_offering = get_object_or_404(ServiceOffering, id=service_offering_id, business=business)
        
        # Check if assignment already exists
        if StaffServiceAssignment.objects.filter(staff_member=staff, service_offering=service_offering).exists():
            messages.warning(request, f'{staff.get_full_name()} is already assigned to {service_offering.name}.')
            return redirect('business:staff_detail', staff_id=staff_id)
        
        # If this is marked as primary, unmark any existing primary assignments
        if is_primary:
            StaffServiceAssignment.objects.filter(staff_member=staff, is_primary=True).update(is_primary=False)
        
        # Create service assignment
        StaffServiceAssignment.objects.create(
            staff_member=staff,
            service_offering=service_offering,
            is_primary=is_primary
        )
        
        messages.success(request, f'{staff.get_full_name()} successfully assigned to {service_offering.name}!')
    except Exception as e:
        messages.error(request, f'Error assigning service: {str(e)}')
    
    return redirect('business:staff_detail', staff_id=staff_id)

@login_required
@require_http_methods(["POST"])
def update_service_assignment(request, staff_id):
    """
    Update an existing service assignment
    Handles form submission from the staff detail page
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        messages.warning(request, 'No business associated with your account.')
        return redirect('accounts:login')
    
    from bookings.models import StaffMember, StaffServiceAssignment
    from business.models import ServiceOffering
    
    # Get staff member, ensuring it belongs to this business
    staff = get_object_or_404(StaffMember, id=staff_id, business=business)
    
    try:
        # Get form data
        assignment_id = request.POST.get('assignment_id')
        service_offering_id = request.POST.get('service_offering')
        is_primary = 'is_primary' in request.POST
        
        # Get the assignment
        assignment = get_object_or_404(StaffServiceAssignment, id=assignment_id, staff_member=staff)
        
        # Get service offering, ensuring it belongs to this business
        service_offering = get_object_or_404(ServiceOffering, id=service_offering_id, business=business)
        
        # Check if changing to a different service that already exists
        if assignment.service_offering != service_offering:
            if StaffServiceAssignment.objects.filter(staff_member=staff, service_offering=service_offering).exists():
                messages.warning(request, f'{staff.get_full_name()} is already assigned to {service_offering.name}.')
                return redirect('business:staff_detail', staff_id=staff_id)
        
        # If this is marked as primary, unmark any existing primary assignments
        if is_primary and not assignment.is_primary:
            StaffServiceAssignment.objects.filter(staff_member=staff, is_primary=True).update(is_primary=False)
        
        # Update assignment
        assignment.service_offering = service_offering
        assignment.is_primary = is_primary
        assignment.save()
        
        messages.success(request, 'Service assignment updated successfully!')
    except Exception as e:
        messages.error(request, f'Error updating service assignment: {str(e)}')
    
    return redirect('business:staff_detail', staff_id=staff_id)

@login_required
@require_http_methods(["POST"])
def delete_service_assignment(request):
    """
    Delete a service assignment via AJAX
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        return JsonResponse({
            'success': False,
            'message': 'No business associated with your account.'
        })
    
    try:
        # Parse JSON data from request body
        data = json.loads(request.body)
        assignment_id = data.get('assignment_id')
        
        from bookings.models import StaffServiceAssignment
        
        # Get assignment, ensuring it belongs to this business
        assignment = get_object_or_404(StaffServiceAssignment, id=assignment_id, staff_member__business=business)
        
        # Delete assignment
        assignment.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Service assignment removed successfully!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

@login_required
@require_http_methods(["POST"])
def delete_staff_role(request):
    """
    Delete a staff role via AJAX
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        return JsonResponse({
            'success': False,
            'message': 'No business associated with your account.'
        })
    
    try:
        # Parse JSON data from request body
        data = json.loads(request.body)
        role_id = data.get('role_id')
        
        from bookings.models import StaffRole
        
        # Get role, ensuring it belongs to this business
        role = get_object_or_404(StaffRole, id=role_id, business=business)
        
        # Check if role is in use
        if role.staff_members.exists():
            return JsonResponse({
                'success': False,
                'message': f'Cannot delete role "{role.name}" because it is assigned to staff members. Remove the role from all staff members first.'
            })
        
        # Store name for success message
        role_name = role.name
        
        # Delete role
        role.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Staff role "{role_name}" deleted successfully!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })


# Staff Account Management Views
@login_required
def staff_accounts(request):
    """
    Render the staff accounts management page
    Shows all staff members with their account status
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        messages.warning(request, 'No business associated with your account.')
        return redirect('accounts:login')
    
    # Get all staff members for this business with their profiles
    from staff.models import StaffProfile
    staff_members = StaffMember.objects.filter(business=business).prefetch_related('roles')
    
    # Add account status to each staff member
    staff_with_accounts = []
    for staff in staff_members:
        has_account = hasattr(staff, 'profile')
        staff_data = {
            'staff': staff,
            'has_account': has_account,
            'profile': staff.profile if has_account else None,
            'user': staff.profile.user if has_account else None,
        }
        staff_with_accounts.append(staff_data)
    
    context = {
        'business': business,
        'staff_with_accounts': staff_with_accounts,
    }
    
    return render(request, 'business/staff_accounts.html', context)


@login_required
@require_http_methods(["POST"])
def create_staff_account(request):
    """
    Create a user account for a staff member
    Handles form submission from the staff accounts page
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        return JsonResponse({
            'success': False,
            'message': 'No business associated with your account.'
        })
    
    try:
        # Parse JSON data from request body
        data = json.loads(request.body)
        staff_id = data.get('staff_id')
        username = data.get('username')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        
        # Validate required fields
        if not staff_id or not username or not password:
            return JsonResponse({
                'success': False,
                'message': 'Staff member, username, and password are required.'
            })
        
        # Validate password match
        if password != confirm_password:
            return JsonResponse({
                'success': False,
                'message': 'Passwords do not match.'
            })
        
        # Validate password strength (minimum 8 characters)
        if len(password) < 8:
            return JsonResponse({
                'success': False,
                'message': 'Password must be at least 8 characters long.'
            })
        
        # Get staff member, ensuring it belongs to this business
        staff_member = get_object_or_404(StaffMember, id=staff_id, business=business)
        
        # Use utility function to create staff account
        from staff.utils import create_staff_user
        from django.core.exceptions import ValidationError
        
        try:
            user, staff_profile = create_staff_user(
                staff_member=staff_member,
                username=username,
                email=staff_member.email,
                password=password,
                is_active=True
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Account created successfully for {staff_member.get_full_name()}!',
                'username': user.username
            })
        except ValidationError as ve:
            return JsonResponse({
                'success': False,
                'message': str(ve)
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })


@login_required
@require_http_methods(["POST"])
def delete_staff_account(request):
    """
    Delete a staff member's user account
    Handles AJAX request from the staff accounts page
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        return JsonResponse({
            'success': False,
            'message': 'No business associated with your account.'
        })
    
    try:
        # Parse JSON data from request body
        data = json.loads(request.body)
        staff_id = data.get('staff_id')
        
        # Get staff member, ensuring it belongs to this business
        staff_member = get_object_or_404(StaffMember, id=staff_id, business=business)
        
        # Use utility function to delete staff account
        from staff.utils import delete_staff_user
        
        if delete_staff_user(staff_member):
            return JsonResponse({
                'success': True,
                'message': f'Account deleted successfully for {staff_member.get_full_name()}!'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Staff member does not have an account.'
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })


@login_required
@require_http_methods(["POST"])
def toggle_staff_account_status(request):
    """
    Activate or deactivate a staff member's user account
    Handles AJAX request from the staff accounts page
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        return JsonResponse({
            'success': False,
            'message': 'No business associated with your account.'
        })
    
    try:
        # Parse JSON data from request body
        data = json.loads(request.body)
        staff_id = data.get('staff_id')
        is_active = data.get('is_active')
        
        # Get staff member, ensuring it belongs to this business
        staff_member = get_object_or_404(StaffMember, id=staff_id, business=business)
        
        # Use utility functions to activate/deactivate
        from staff.utils import activate_staff_user, deactivate_staff_user
        
        if is_active:
            if activate_staff_user(staff_member):
                return JsonResponse({
                    'success': True,
                    'message': f'Account activated for {staff_member.get_full_name()}!'
                })
        else:
            if deactivate_staff_user(staff_member):
                return JsonResponse({
                    'success': True,
                    'message': f'Account deactivated for {staff_member.get_full_name()}!'
                })
        
        return JsonResponse({
            'success': False,
            'message': 'Staff member does not have an account.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })


@login_required
@require_http_methods(["POST"])
def reset_staff_account_password(request):
    """
    Reset a staff member's password
    Handles AJAX request from the staff accounts page
    """
    # Get business for either business owner or staff user
    business = get_user_business(request.user)
    if not business:
        return JsonResponse({
            'success': False,
            'message': 'No business associated with your account.'
        })
    
    try:
        # Parse JSON data from request body
        data = json.loads(request.body)
        staff_id = data.get('staff_id')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        # Validate required fields
        if not staff_id or not new_password:
            return JsonResponse({
                'success': False,
                'message': 'Staff member and new password are required.'
            })
        
        # Validate password match
        if new_password != confirm_password:
            return JsonResponse({
                'success': False,
                'message': 'Passwords do not match.'
            })
        
        # Validate password strength
        if len(new_password) < 8:
            return JsonResponse({
                'success': False,
                'message': 'Password must be at least 8 characters long.'
            })
        
        # Get staff member, ensuring it belongs to this business
        staff_member = get_object_or_404(StaffMember, id=staff_id, business=business)
        
        # Use utility function to reset password
        from staff.utils import reset_staff_password

        print(new_password)
        
        if reset_staff_password(staff_member, new_password):
            return JsonResponse({
                'success': True,
                'message': f'Password reset successfully for {staff_member.get_full_name()}!'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Staff member does not have an account.'
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

