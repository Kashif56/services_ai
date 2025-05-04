from django.utils import timezone
from datetime import datetime, timedelta, time
from django.db.models import Q

from bookings.models import (
    StaffMember, 
    StaffAvailability, 
    Booking, 
    BookingStatus, 
    AVAILABILITY_TYPE, 
    BookingStaffAssignment,
    Business
)


def check_timeslot_availability(business, start_time, duration_minutes, service=None):
    """
    Check if a specific time slot is available.
    
    Args:
        business: Business object or ID
        start_time: Datetime object for the start time
        duration_minutes: Duration of the appointment in minutes
        service: Optional ServiceOffering object
        
    Returns:
        Tuple of (is_available, reason)
    """
    try:
        print(f"[DEBUG] check_timeslot_availability called with: business={business}, start_time={start_time}, duration_minutes={duration_minutes}, service={service}")
        
        # Convert business ID to object if needed
        if not isinstance(business, Business):
            try:
                print(f"[DEBUG] Converting business ID to object: {business}")
                business = Business.objects.get(id=business)
                print(f"[DEBUG] Found business: {business.name}")
            except Business.DoesNotExist:
                print(f"[DEBUG] Business with ID {business} not found")
                return False, f"Business with ID {business} not found"
        
        # Calculate end time
        end_time = start_time + timedelta(minutes=duration_minutes)
        print(f"[DEBUG] Calculated end time: {end_time}")
        
        # Check if the business is open during this time
        weekday = start_time.weekday()
        business_hours = _get_business_hours(business, weekday)
        
        print(f"[DEBUG] Business hours for weekday {weekday}: {business_hours}")
        
        if not business_hours:
            print(f"[DEBUG] Business is closed on this day")
            return False, "Business is closed on this day"
        
        # Check if the time falls within business hours
        is_within_hours = False
        for hours in business_hours:
            start_hour, start_minute = map(int, hours['start'].split(':'))
            end_hour, end_minute = map(int, hours['end'].split(':'))
            
            business_start = time(start_hour, start_minute)
            business_end = time(end_hour, end_minute)
            
            # Handle time slots that cross midnight
            booking_start_time = start_time.time()
            booking_end_time = end_time.time()
            
            # Normal case: both start and end times are on the same day
            if booking_end_time > booking_start_time:
                if (booking_start_time >= business_start and 
                    booking_end_time <= business_end):
                    is_within_hours = True
                    break
            # Special case: booking crosses midnight
            else:
                # For bookings that cross midnight, we need to check if either:
                # 1. The start time is within business hours (for the first day)
                # 2. The end time is within business hours (for the next day)
                # Since we're only checking one day at a time, we'll only validate
                # if the start time is within business hours for this day
                if booking_start_time >= business_start and business_end >= time(23, 59):
                    is_within_hours = True
                    break
                # If business hours don't extend to midnight, this time slot is not valid
                print(f"[DEBUG] Booking crosses midnight but business hours end before midnight")
        
        if not is_within_hours:
            print(f"[DEBUG] Time is outside business hours")
            return False, "Time is outside business hours"
        
        # Check if there are any conflicting bookings
        try:
            # Get all valid booking status values
            valid_statuses = []
            for status in BookingStatus:
                valid_statuses.append(status)
            
            print(f"[DEBUG] Valid booking statuses: {valid_statuses}")
            
            # Use 'CONFIRMED' status or whatever is available
            confirmed_status = None
            for status in valid_statuses:
                if str(status).upper() == 'CONFIRMED':
                    confirmed_status = status
                    break
            
            if confirmed_status:
                print(f"[DEBUG] Using confirmed status: {confirmed_status}")
                conflicting_bookings = Booking.objects.filter(
                    business=business,
                    start_time__lt=end_time,
                    end_time__gt=start_time,
                    status=confirmed_status
                )
            else:
                print(f"[DEBUG] No confirmed status found, checking all bookings")
                conflicting_bookings = Booking.objects.filter(
                    business=business,
                    start_time__lt=end_time,
                    end_time__gt=start_time
                )
            
            print(f"[DEBUG] Found {conflicting_bookings.count()} conflicting bookings")
            
            if conflicting_bookings.exists():
                return False, "Time slot conflicts with existing bookings"
                
        except Exception as e:
            print(f"[DEBUG] Error checking conflicting bookings: {str(e)}")
            # If there's an error with the booking fields, return a generic message
            return False, "Unable to check booking conflicts"
        
        # Check if any staff is available
        try:
            all_staff = StaffMember.objects.filter(business=business, is_active=True)
            
            print(f"[DEBUG] Checking availability for {all_staff.count()} staff members")
            
            if not all_staff.exists():
                print(f"[DEBUG] No staff members found for this business")
                return False, "No staff members found for this business"
            
            # For each staff member, check if they're available
            available_staff = []
            for staff in all_staff:
                try:
                    # Use the is_staff_available function from the original implementation
                    # which works with the existing database schema
                    if is_staff_available(staff, start_time.date(), start_time.time(), end_time.time()):
                        available_staff.append(staff)
                        print(f"[DEBUG] Staff {staff.id} is available")
                except Exception as e:
                    print(f"[DEBUG] Error checking availability for staff {staff.id}: {str(e)}")
                    # Continue to the next staff member
                    continue
            
            print(f"[DEBUG] Found {len(available_staff)} available staff members")
            
            if not available_staff:
                return False, "No staff available at this time"
            
            return True, "Available"
            
        except Exception as e:
            print(f"[DEBUG] Error checking staff availability: {str(e)}")
            # If there's an error, assume no staff is available
            return False, "Unable to check staff availability"
    
    except Exception as e:
        import traceback
        print(f"[DEBUG] Error in check_timeslot_availability: {str(e)}")
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        return False, f"Error checking availability: {str(e)}"

def _is_staff_available(staff, start_time, end_time):
    """
    Check if a staff member is available during a specific time slot.
    
    Args:
        staff: StaffMember object
        start_time: Datetime object for the start time
        end_time: Datetime object for the end time
        
    Returns:
        bool: True if staff is available, False otherwise
    """
    print(f"[DEBUG] _is_staff_available called with: staff={staff.id}, start_time={start_time}, end_time={end_time}")
    
    date = start_time.date()
    weekday = date.weekday()
    
    # First check specific date availability/unavailability (higher priority)
    try:
        specific_availabilities = StaffAvailability.objects.filter(
            staff_member=staff,  # Use staff_member instead of staff
            specific_date=date
        )
        
        print(f"[DEBUG] Found {specific_availabilities.count()} specific date availabilities")
        
        if specific_availabilities.exists():
            # Check if any specific date rule marks this time as unavailable
            for avail in specific_availabilities:
                if not avail.is_available:
                    # This is an "off day" record - check if time overlaps with the off period
                    if (start_time < avail.end_time and end_time > avail.start_time):
                        print(f"[DEBUG] Staff {staff.id} has off day record overlapping with booking time")
                        return False
                else:
                    # This is an "available" record - check if time is fully contained in the available period
                    if (start_time >= avail.start_time and end_time <= avail.end_time):
                        print(f"[DEBUG] Staff {staff.id} has available record containing booking time")
                        return True
            
            # If we have specific date rules but none explicitly allow this time, staff is unavailable
            print(f"[DEBUG] Staff {staff.id} has specific date rules but none allow this time")
            return False
        
        # Check weekly availability if no specific date rules exist
        weekly_availabilities = StaffAvailability.objects.filter(
            staff_member=staff,  # Use staff_member instead of staff
            weekday=weekday,
            specific_date__isnull=True
        )
        
        print(f"[DEBUG] Found {weekly_availabilities.count()} weekly availabilities")
        
        if weekly_availabilities.exists():
            # Check if any weekly rule marks this time as unavailable
            for avail in weekly_availabilities:
                if not avail.is_available:
                    # This is an "off day" record - check if time overlaps with the off period
                    if (start_time.time() < avail.end_time and end_time.time() > avail.start_time):
                        print(f"[DEBUG] Staff {staff.id} has off day record overlapping with booking time")
                        return False
                else:
                    # This is an "available" record - check if time is fully contained in the available period
                    if (start_time.time() >= avail.start_time and end_time.time() <= avail.end_time):
                        print(f"[DEBUG] Staff {staff.id} has available record containing booking time")
                        return True
            
            # If we have weekly rules but none explicitly allow this time, staff is unavailable
            print(f"[DEBUG] Staff {staff.id} has weekly rules but none allow this time")
            return False
        
        # If no availability rules exist for this day, staff is considered available by default
        print(f"[DEBUG] Staff {staff.id} has no availability rules for this day - considering available by default")
        return True
    
    except Exception as e:
        import traceback
        print(f"[DEBUG] Error checking staff availability: {str(e)}")
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        # If there's an error, assume staff is available to avoid blocking bookings
        return True

def _get_business_hours(business, weekday):
    """
    Get business hours for a specific weekday.
    
    Args:
        business: Business object
        weekday: Integer representing weekday (0=Monday, 6=Sunday)
        
    Returns:
        List of dicts with start and end times
    """
    print(f"[DEBUG] _get_business_hours called with: business={business.id}, weekday={weekday}")
    
    # Default business hours (9 AM to 5 PM)
    default_hours = [{'start': '09:00', 'end': '17:00'}]
    
    # TODO: Implement business hours from database
    # For now, return default hours for weekdays (Monday-Friday)
    if 0 <= weekday <= 4:  # Monday to Friday
        print(f"[DEBUG] Returning default weekday hours")
        return default_hours
    else:  # Weekend
        print(f"[DEBUG] Business closed on weekend")
        return []  # Closed on weekends


def get_alternate_timeslots(business_id, date, start_time, duration_minutes, service_offering_id=None, staff_member_id=None):
    """
    Find alternate available timeslots when the requested slot is unavailable.
    
    Args:
        business_id (UUID): ID of the business
        date (date): Date to check
        start_time (time): Start time that was unavailable
        duration_minutes (int): Duration of the appointment in minutes
        service_offering_id (UUID, optional): ID of the service offering
        staff_member_id (UUID, optional): ID of a specific staff member to check
        
    Returns:
        list: List of dicts with alternate date/time options
    """
    print(f"[DEBUG] get_alternate_timeslots called with: business_id={business_id}, date={date}, start_time={start_time}, duration_minutes={duration_minutes}, service_offering_id={service_offering_id}, staff_member_id={staff_member_id}")
    
    alternate_slots = []
    current_date = date
    
    # Try same day, different times
    same_day_slots = find_available_slots_on_date(
        business_id, 
        current_date, 
        duration_minutes, 
        None, 
        staff_member_id,
        max_slots=3
    )
    
    alternate_slots.extend(same_day_slots)
    
    print(f"[DEBUG] Found {len(alternate_slots)} alternate slots on same day")
    
    # If we don't have enough slots, try the next day
    if len(alternate_slots) < 3:
        next_day = current_date + timedelta(days=1)
        next_day_slots = find_available_slots_on_date(
            business_id, 
            next_day, 
            duration_minutes, 
            None, 
            staff_member_id,
            max_slots=3 - len(alternate_slots)
        )
        alternate_slots.extend(next_day_slots)
        
        print(f"[DEBUG] Found {len(alternate_slots)} alternate slots on next day")
    
    # If we still don't have enough slots, try two days later
    if len(alternate_slots) < 3:
        two_days_later = current_date + timedelta(days=2)
        two_days_later_slots = find_available_slots_on_date(
            business_id, 
            two_days_later, 
            duration_minutes, 
            None, 
            staff_member_id,
            max_slots=3 - len(alternate_slots)
        )
        alternate_slots.extend(two_days_later_slots)
        
        print(f"[DEBUG] Found {len(alternate_slots)} alternate slots on two days later")
    
    return alternate_slots


def find_available_slots_on_date(business_id, date, duration_minutes, service_offering_id=None, staff_member_id=None, max_slots=3):
    """
    Find available time slots on a specific date.
    
    Args:
        business_id (UUID): ID of the business
        date (date): Date to check
        duration_minutes (int): Duration of the appointment in minutes
        service_offering_id (UUID, optional): ID of the service offering
        staff_member_id (UUID, optional): ID of a specific staff member to check
        max_slots (int): Maximum number of slots to return
        
    Returns:
        list: List of dicts with available time slots
    """
    print(f"[DEBUG] find_available_slots_on_date called with: business_id={business_id}, date={date}, duration_minutes={duration_minutes}, service_offering_id={service_offering_id}, staff_member_id={staff_member_id}, max_slots={max_slots}")
    
    available_slots = []
    
    # Get qualified staff members
    staff_query = Q(business_id=business_id, is_active=True, is_available=True)
    
    if staff_member_id:
        staff_query &= Q(id=staff_member_id)
    
    qualified_staff = StaffMember.objects.filter(staff_query).distinct()
    
    print(f"[DEBUG] Found {qualified_staff.count()} qualified staff members")
    
    if not qualified_staff.exists():
        return []
    
    # Get all existing bookings for this date
    existing_bookings = Booking.objects.filter(
        business_id=business_id,
        booking_date=date,
        status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.RESCHEDULED]
    ).order_by('start_time')
    
    print(f"[DEBUG] Found {existing_bookings.count()} existing bookings")
    
    # Define standard business hours (can be customized based on business settings)
    business_start = time(9, 0)  # 9:00 AM
    business_end = time(17, 0)   # 5:00 PM
    
    # If checking for today, start from current time
    if date == timezone.now().date() and timezone.now().time() > business_start:
        current_time = timezone.now().time()
        # Round up to the nearest half hour
        minutes = current_time.minute
        if minutes < 30:
            business_start = time(current_time.hour, 30)
        else:
            business_start = time(current_time.hour + 1, 0)
    
    # Generate potential time slots at 30-minute intervals
    slot_interval = 30  # minutes
    slot_start = datetime.combine(date, business_start)
    slot_end = datetime.combine(date, business_end)
    
    print(f"[DEBUG] Generating potential time slots from {slot_start} to {slot_end}")
    
    # Track which staff members are booked at which times
    staff_bookings = {}
    for staff in qualified_staff:
        staff_bookings[str(staff.id)] = []
        
    # Populate staff bookings
    for booking in existing_bookings:
        staff_assignments = BookingStaffAssignment.objects.filter(booking=booking)
        for assignment in staff_assignments:
            staff_id = str(assignment.staff_member.id)
            if staff_id in staff_bookings:
                staff_bookings[staff_id].append({
                    'start': datetime.combine(date, booking.start_time),
                    'end': datetime.combine(date, booking.end_time)
                })
    
    print(f"[DEBUG] Populated staff bookings")
    
    # Track which slots we've already added to avoid duplicates
    added_slots = set()
    
    current_slot = slot_start
    while current_slot + timedelta(minutes=duration_minutes) <= slot_end and len(available_slots) < max_slots:
        slot_start_time = current_slot.time()
        slot_end_time = (current_slot + timedelta(minutes=duration_minutes)).time()
        
        slot_key = f"{slot_start_time.strftime('%H:%M')}-{slot_end_time.strftime('%H:%M')}"
        
        # Skip if we already added this slot
        if slot_key in added_slots:
            current_slot += timedelta(minutes=slot_interval)
            continue
        
        # Check if any staff member is available for this slot
        for staff in qualified_staff:
            staff_id = str(staff.id)
            
            # Check if staff has an overlapping booking
            has_overlap = False
            slot_start_dt = datetime.combine(date, slot_start_time)
            slot_end_dt = datetime.combine(date, slot_end_time)
            
            for booking in staff_bookings.get(staff_id, []):
                if (slot_start_dt < booking['end'] and slot_end_dt > booking['start']):
                    has_overlap = True
                    break
            
            if has_overlap:
                print(f"[DEBUG] Staff {staff_id} has overlapping booking")
                continue
                
            # Check staff availability
            if is_staff_available(staff, date, slot_start_time, slot_end_time):
                print(f"[DEBUG] Staff {staff_id} is available")
                # Add this slot to available slots
                available_slots.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'time': slot_start_time.strftime('%H:%M'),
                    'end_time': slot_end_time.strftime('%H:%M'),
                    'staff': {
                        'id': str(staff.id),
                        'name': staff.get_full_name()
                    }
                })
                
                # Mark this slot as added
                added_slots.add(slot_key)
                
                # Also mark this time as booked for this staff member to avoid suggesting overlapping slots
                staff_bookings[staff_id].append({
                    'start': slot_start_dt,
                    'end': slot_end_dt
                })
                
                break  # Found an available staff for this slot
        
        # Move to next slot
        current_slot += timedelta(minutes=slot_interval)
    
    print(f"[DEBUG] Found {len(available_slots)} available slots")
    for slot in available_slots:
        print(f"[DEBUG] Available slot: {slot['date']} {slot['time']}-{slot['end_time']} with {slot['staff']['name']}")
    
    return available_slots

def is_staff_available(staff, booking_date, booking_start_time, booking_end_time):
    """
    Check if a staff member is available at the given date and time.
    
    Args:
        staff (StaffMember): Staff member to check
        booking_date (date): Date of the booking
        booking_start_time (time): Start time of the booking
        booking_end_time (time): End time of the booking
        
    Returns:
        bool: True if staff is available, False otherwise
    """
    print(f"[DEBUG] is_staff_available called with: staff={staff.id}, booking_date={booking_date}, booking_start_time={booking_start_time}, booking_end_time={booking_end_time}")
    
    weekday = booking_date.weekday()
    
    # First check specific date availability/unavailability (higher priority)
    try:
        specific_availabilities = staff.availability.filter(
            availability_type=AVAILABILITY_TYPE.SPECIFIC,
            specific_date=booking_date
        )
        
        print(f"[DEBUG] Found {specific_availabilities.count()} specific date availabilities")
        
        if specific_availabilities.exists():
            # Check if any specific date rule marks this time as unavailable
            for avail in specific_availabilities:
                if avail.off_day:
                    # This is an "off day" record - check if time overlaps with the off period
                    if (booking_start_time < avail.end_time and booking_end_time > avail.start_time):
                        print(f"[DEBUG] Staff {staff.id} has off day record overlapping with booking time")
                        return False
                else:
                    # This is an "available" record - check if time is fully contained in the available period
                    # Handle case where booking crosses midnight
                    if booking_end_time < booking_start_time:  # Crosses midnight
                        # For bookings that cross midnight, check if the start time is within the available period
                        # and the available period extends to midnight
                        if (booking_start_time >= avail.start_time and avail.end_time >= time(23, 59)):
                            print(f"[DEBUG] Staff {staff.id} has available record containing booking start time (crosses midnight)")
                            return True
                    else:  # Normal case: both start and end times are on the same day
                        if (booking_start_time >= avail.start_time and booking_end_time <= avail.end_time):
                            print(f"[DEBUG] Staff {staff.id} has available record containing booking time")
                            return True
            
            # If we have specific date rules but none explicitly allow this time, staff is unavailable
            print(f"[DEBUG] Staff {staff.id} has specific date rules but none allow this time")
            return False
        
        # Check weekly availability if no specific date rules exist
        weekly_availabilities = staff.availability.filter(
            availability_type=AVAILABILITY_TYPE.WEEKLY,
            weekday=weekday
        )
        
        print(f"[DEBUG] Found {weekly_availabilities.count()} weekly availabilities")
        
        if weekly_availabilities.exists():
            # Check if any weekly rule marks this time as unavailable
            for avail in weekly_availabilities:
                if avail.off_day:
                    # This is an "off day" record - check if time overlaps with the off period
                    if (booking_start_time < avail.end_time and booking_end_time > avail.start_time):
                        print(f"[DEBUG] Staff {staff.id} has off day record overlapping with booking time")
                        return False
                else:
                    # This is an "available" record - check if time is fully contained in the available period
                    # Handle case where booking crosses midnight
                    if booking_end_time < booking_start_time:  # Crosses midnight
                        # For bookings that cross midnight, check if the start time is within the available period
                        # and the available period extends to midnight
                        if (booking_start_time >= avail.start_time and avail.end_time >= time(23, 59)):
                            print(f"[DEBUG] Staff {staff.id} has available record containing booking start time (crosses midnight)")
                            return True
                    else:  # Normal case: both start and end times are on the same day
                        if (booking_start_time >= avail.start_time and booking_end_time <= avail.end_time):
                            print(f"[DEBUG] Staff {staff.id} has available record containing booking time")
                            return True
            
            # If we have weekly rules but none explicitly allow this time, staff is unavailable
            print(f"[DEBUG] Staff {staff.id} has weekly rules but none allow this time")
            return False
        
        # If no availability rules exist for this day, staff is considered unavailable by default
        print(f"[DEBUG] Staff {staff.id} has no availability rules for this day")
        return False

    except Exception as e:
        import traceback
        print(f"[DEBUG] Error checking staff availability: {str(e)}")
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        # If there's an error, assume staff is available to avoid blocking bookings
        return True
