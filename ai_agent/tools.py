from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Type, Annotated
from datetime import datetime, timedelta
import pytz
from django.utils import timezone
from django.db.models import Q

from bookings.models import Booking, BookingStatus, StaffAvailability, StaffMember, BookingStaffAssignment, BookingServiceItem
from business.models import Business, ServiceOffering, ServiceItem, ServiceOfferingItem
from leads.models import Lead
from bookings.availability import check_timeslot_availability, find_available_slots_on_date, is_staff_available
from decimal import Decimal

class CheckAvailabilityInput(BaseModel):
    """Input for checking availability."""
    date: str = Field(..., description="The date to check availability in format YYYY-MM-DD")
    time: Optional[str] = Field(None, description="The time to check availability in format HH:MM")
    service_name: Optional[str] = Field(None, description="Name of the service")
    business_id: str = Field(..., description="ID of the business")
    duration_minutes: Optional[int] = Field(None, description="Duration of the appointment in minutes")

class CheckAvailabilityTool(BaseTool):
    name: str = "check_availability"
    description: str = "Check availability for appointments on a specific date and time"
    args_schema: Type[BaseModel] = CheckAvailabilityInput
    
    def _run(self, date: str, time: Optional[str] = None, 
             service_name: Optional[str] = None, business_id: str = None,
             duration_minutes: Optional[int] = None) -> str:
        try:
            print(f"[DEBUG] CheckAvailabilityTool called with: date={date}, time={time}, service_name={service_name}, business_id={business_id}, duration_minutes={duration_minutes}")
            
            # Get the business
            try:
                # Try to get by ID first
                try:
                    # Check if business_id is a valid ID
                    print(f"[DEBUG] Attempting to find business with ID: {business_id}")
                    business = Business.objects.get(id=business_id)
                    print(f"[DEBUG] Found business by ID: {business.name}")
                except (Business.DoesNotExist) as e:
                    print(f"[DEBUG] Business not found with ID: {str(e)}")
                    # If not found by ID, try to find by name
                    print(f"[DEBUG] Trying to find business by name: {business_id}")
                    business = Business.objects.filter(name__iexact=business_id).first()
                    if not business:
                        print(f"[DEBUG] Business with name '{business_id}' not found")
                        return f"Business with name '{business_id}' not found. Please use a valid business ID."
                    print(f"[DEBUG] Found business by name: {business.name} (ID: {business.id})")
            except Exception as e:
                print(f"[DEBUG] Error finding business: {str(e)}")
                return f"Error finding business: {str(e)}"
            
            # Parse the date
            try:
                print(f"[DEBUG] Parsing date: {date}")
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                print(f"[DEBUG] Parsed date: {date_obj}")
                
                # Check if date is in the past
                today = timezone.now().date()
                print(f"[DEBUG] Today's date: {today}")
                if date_obj < today:
                    print(f"[DEBUG] Date {date} is in the past")
                    return f"The date {date} is in the past. Please select a current or future date."
                
            except ValueError as e:
                print(f"[DEBUG] Invalid date format: {date}, error: {str(e)}")
                return f"Invalid date format: {date}. Please use YYYY-MM-DD format."
            
            # If time is provided, check specific time slot
            if time:
                try:
                    print(f"[DEBUG] Parsing time: {time}")
                    # Parse the time
                    time_obj = datetime.strptime(time, '%H:%M').time()
                    print(f"[DEBUG] Parsed time: {time_obj}")
                    
                    # Get service if provided
                    service = None
                    if service_name:
                        try:
                            print(f"[DEBUG] Looking for service: {service_name}")
                            service = ServiceOffering.objects.get(
                                business=business,
                                name__iexact=service_name,
                                is_active=True
                            )
                            print(f"[DEBUG] Found service: {service.name} (ID: {service.id})")
                            # Use service duration if no duration provided
                            if not duration_minutes:
                                duration_minutes = service.duration
                                print(f"[DEBUG] Using service duration: {duration_minutes} minutes")
                        except ServiceOffering.DoesNotExist:
                            print(f"[DEBUG] Service '{service_name}' not found")
                            return f"Service '{service_name}' not found for business '{business.name}'."
                    
                    # Use default duration if not specified
                    if not duration_minutes:
                        duration_minutes = 60  # Default duration
                        print(f"[DEBUG] Using default duration: {duration_minutes} minutes")
                    
                    # Create datetime object for the appointment
                    # Use UTC timezone as default since the Business model doesn't have a timezone field
                    print(f"[DEBUG] Using default timezone: UTC")
                    tz = pytz.UTC
                    appointment_datetime = tz.localize(
                        datetime.combine(date_obj, time_obj)
                    )
                    print(f"[DEBUG] Appointment datetime: {appointment_datetime}")
                    
                    # Check if the time is in the past
                    now = timezone.now()
                    print(f"[DEBUG] Current time: {now}")
                    if appointment_datetime < now:
                        print(f"[DEBUG] Time {time} on {date} is in the past")
                        return f"The time {time} on {date} is in the past. Please select a current or future time."
                    
                    # Check availability
                    print(f"[DEBUG] Checking availability with check_timeslot_availability")
                    print(f"[DEBUG] Parameters: business={business.id}, start_time={appointment_datetime}, duration_minutes={duration_minutes}, service={service.id if service else None}")
                    
                    try:
                        is_available, reason, _ = check_timeslot_availability(
                            business=business,
                            start_time=appointment_datetime,
                            duration_minutes=duration_minutes,
                            service=service
                        )
                        print(f"[DEBUG] Availability result: is_available={is_available}, reason={reason}")
                    except Exception as e:
                        import traceback
                        print(f"[DEBUG] Error in check_timeslot_availability: {str(e)}")
                        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
                        raise
                    
                    if is_available:
                        return f"The time slot at {time} on {date} is available for booking."
                    else:
                        # Find alternative slots
                        print(f"[DEBUG] Finding alternative slots with find_available_slots_on_date")
                        try:
                            # Check if we need to use the old or new interface
                            import inspect
                            params = inspect.signature(find_available_slots_on_date).parameters
                            
                            if 'business' in params:
                                # New interface
                                alternative_slots = find_available_slots_on_date(
                                    business=business,
                                    date=date_obj,
                                    duration_minutes=duration_minutes,
                                    service=service
                                )
                            else:
                                # Old interface
                                alternative_slots = find_available_slots_on_date(
                                    business_id=str(business.id),
                                    date=date_obj,
                                    duration_minutes=duration_minutes,
                                    service_offering_id=service.id if service else None
                                )
                            
                            print(f"[DEBUG] Found {len(alternative_slots)} alternative slots")
                        except Exception as e:
                            import traceback
                            print(f"[DEBUG] Error in find_available_slots_on_date: {str(e)}")
                            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
                            raise
                        
                        if alternative_slots:
                            # Handle different return formats
                            if isinstance(alternative_slots[0], datetime):
                                alt_slots_formatted = [slot.strftime('%H:%M') for slot in alternative_slots[:5]]
                            else:
                                alt_slots_formatted = [slot['time'] for slot in alternative_slots[:5]]
                                
                            alt_slots_str = ", ".join(alt_slots_formatted)
                            return f"The time slot at {time} on {date} is not available. Reason: {reason}. Alternative available times on this date: {alt_slots_str}."
                        else:
                            return f"The time slot at {time} on {date} is not available. Reason: {reason}. There are no alternative times available on this date."
                
                except ValueError as e:
                    print(f"[DEBUG] Invalid time format: {time}, error: {str(e)}")
                    return f"Invalid time format: {time}. Please use HH:MM format."
            
            # If no time provided, find all available slots for the date
            else:
                # Get service if provided
                service = None
                if service_name:
                    try:
                        service = ServiceOffering.objects.get(
                            business=business,
                            name__iexact=service_name,
                            is_active=True
                        )
                        # Use service duration if no duration provided
                        if not duration_minutes:
                            duration_minutes = service.duration
                    except ServiceOffering.DoesNotExist:
                        return f"Service '{service_name}' not found for business '{business.name}'."
                
                # Use default duration if not specified
                if not duration_minutes:
                    duration_minutes = 60  # Default duration
                
                # Find available slots
                available_slots = find_available_slots_on_date(
                    business=business,
                    date=date_obj,
                    duration_minutes=duration_minutes,
                    service=service
                )
                
                if available_slots:
                    # Handle different return formats
                    if isinstance(available_slots[0], datetime):
                        slots_formatted = [slot.strftime('%H:%M') for slot in available_slots[:10]]
                    else:
                        slots_formatted = [slot['time'] for slot in available_slots[:10]]
                        
                    slots_str = ", ".join(slots_formatted)
                    return f"Available time slots on {date} for {business.name}: {slots_str}."
                else:
                    return f"No available time slots found on {date} for {business.name}."
        
        except Exception as e:
            import traceback
            print(f"[DEBUG] Error in CheckAvailabilityTool: {str(e)}")
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return f"An error occurred while checking availability: {str(e)}\n{traceback.format_exc()}"

class BookAppointmentInput(BaseModel):
    """Input for booking an appointment."""
    date: str = Field(..., description="The date for the appointment in format YYYY-MM-DD")
    time: str = Field(..., description="The time for the appointment in format HH:MM")
    service_name: str = Field(..., description="Name of the service")
    business_id: str = Field(..., description="ID of the business")
    customer_name: str = Field(..., description="Name of the customer")
    customer_phone: str = Field(..., description="Phone number of the customer")
    customer_email: Optional[str] = Field(None, description="Email of the customer")
    service_items: Optional[List[Dict[str, Any]]] = Field(None, description="List of service items with identifiers and quantities")
    notes: Optional[str] = Field(None, description="Additional notes for the appointment")

class BookAppointmentTool(BaseTool):
    name: str = "book_appointment"
    description: str = "Book an appointment for a customer"
    args_schema: Type[BaseModel] = BookAppointmentInput
    
    def _run(self, date: str, time: str, service_name: str, business_id: str,
             customer_name: str, customer_phone: str, customer_email: Optional[str] = None,
             service_items: Optional[List[Dict[str, Any]]] = None,
             notes: Optional[str] = None) -> str:
        try:
            print(f"[DEBUG] BookAppointmentTool called with: date={date}, time={time}, service_name={service_name}, business_id={business_id}, customer_name={customer_name}, customer_phone={customer_phone}, customer_email={customer_email}, service_items={service_items}, notes={notes}")
            
            # Get the business
            try:
                # Try to get by ID first
                try:
                    from uuid import UUID
                    # Check if business_id is a valid UUID
                    print(f"[DEBUG] Attempting to parse business_id as UUID: {business_id}")
                    uuid_obj = UUID(business_id, version=4)
                    business = Business.objects.get(id=uuid_obj)
                    print(f"[DEBUG] Found business by UUID: {business.name}")
                except (ValueError, TypeError) as e:
                    print(f"[DEBUG] business_id is not a valid UUID: {str(e)}")
                    # If not a valid UUID, try to find by name
                    print(f"[DEBUG] Trying to find business by name: {business_id}")
                    business = Business.objects.filter(name__iexact=business_id).first()
                    if not business:
                        print(f"[DEBUG] Business with name '{business_id}' not found")
                        return f"Business with name '{business_id}' not found. Please use a valid business ID."
                    print(f"[DEBUG] Found business by name: {business.name} (ID: {business.id})")
            except Business.DoesNotExist:
                print(f"[DEBUG] Business with ID {business_id} not found")
                return f"Business with ID {business_id} not found."
            
            # Parse the date and time
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                time_obj = datetime.strptime(time, '%H:%M').time()
                
                # Check if date is in the past
                today = timezone.now().date()
                print(f"[DEBUG] Today's date: {today}")
                if date_obj < today:
                    print(f"[DEBUG] Date {date} is in the past")
                    return f"The date {date} is in the past. Please select a current or future date."
                
                # Create datetime object for the appointment
                # Use UTC timezone as default since the Business model doesn't have a timezone field
                print(f"[DEBUG] Using default timezone: UTC")
                tz = pytz.UTC
                appointment_datetime = tz.localize(
                    datetime.combine(date_obj, time_obj)
                )
                print(f"[DEBUG] Appointment datetime: {appointment_datetime}")
                
                # Check if the time is in the past
                now = timezone.now()
                print(f"[DEBUG] Current time: {now}")
                if appointment_datetime < now:
                    print(f"[DEBUG] Time {time} on {date} is in the past")
                    return f"The time {time} on {date} is in the past. Please select a current or future time."
                
            except ValueError as e:
                if 'time' in str(e):
                    return f"Invalid time format: {time}. Please use HH:MM format."
                else:
                    return f"Invalid date format: {date}. Please use YYYY-MM-DD format."
            
            # Get the service
            try:
                print(f"[DEBUG] Looking for service: {service_name}")
                service = ServiceOffering.objects.get(
                    business=business,
                    name__iexact=service_name,
                    is_active=True
                )
                print(f"[DEBUG] Found service: {service.name} (ID: {service.id})")
            except ServiceOffering.DoesNotExist:
                print(f"[DEBUG] Service '{service_name}' not found")
                return f"Service '{service_name}' not found for business '{business.name}'."
            
            # Check availability
            print(f"[DEBUG] Checking availability with check_timeslot_availability")
            try:
                is_available, reason, _available_staff = check_timeslot_availability(
                    business=business,
                    start_time=appointment_datetime,
                    duration_minutes=service.duration,
                    service=service
                )
                print(f"[DEBUG] Availability result: is_available={is_available}, reason={reason}")
            except Exception as e:
                import traceback
                print(f"[DEBUG] Error in check_timeslot_availability: {str(e)}")
                print(f"[DEBUG] Traceback: {traceback.format_exc()}")
                return f"Error checking availability: {str(e)}"
            
            if not is_available:
                # Find alternative slots
                print(f"[DEBUG] Finding alternative slots with find_available_slots_on_date")
                try:
                    alternative_slots = find_available_slots_on_date(
                        business=business,
                        date=date_obj,
                        duration_minutes=service.duration,
                        service=service
                    )
                    print(f"[DEBUG] Found {len(alternative_slots)} alternative slots")
                except Exception as e:
                    import traceback
                    print(f"[DEBUG] Error in find_available_slots_on_date: {str(e)}")
                    print(f"[DEBUG] Traceback: {traceback.format_exc()}")
                    return f"Error finding alternative slots: {str(e)}"
                
                if alternative_slots:
                    # Handle different return formats
                    if isinstance(alternative_slots[0], datetime):
                        alt_slots_formatted = [slot.strftime('%H:%M') for slot in alternative_slots[:5]]
                    else:
                        alt_slots_formatted = [slot['time'] for slot in alternative_slots[:5]]
                        
                    alt_slots_str = ", ".join(alt_slots_formatted)
                    return f"Cannot book appointment at {time} on {date}. Reason: {reason}. Alternative available times on this date: {alt_slots_str}."
                else:
                    return f"Cannot book appointment at {time} on {date}. Reason: {reason}. There are no alternative times available on this date."
            
            # Find or create lead
            try:
                print(f"[DEBUG] Finding or creating lead with phone: {customer_phone}")
                
                # Split customer name into first and last name
                name_parts = customer_name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                lead, created = Lead.objects.get_or_create(
                    phone=customer_phone,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': customer_email,
                        'business': business,
                        'source': 'ai_agent'
                    }
                )
                
                if created:
                    print(f"[DEBUG] Created new lead: {lead.id}")
                else:
                    print(f"[DEBUG] Found existing lead: {lead.id}")
                
                # If lead exists but some fields are empty, update them
                if not created:
                    updated_fields = []
                    if not lead.first_name and first_name:
                        lead.first_name = first_name
                        updated_fields.append('first_name')
                    if not lead.last_name and last_name:
                        lead.last_name = last_name
                        updated_fields.append('last_name')
                    if not lead.email and customer_email:
                        lead.email = customer_email
                        updated_fields.append('email')
                    
                    if updated_fields:
                        lead.save(update_fields=updated_fields)
                        print(f"[DEBUG] Updated lead fields: {updated_fields}")
            except Exception as e:
                import traceback
                print(f"[DEBUG] Error finding/creating lead: {str(e)}")
                print(f"[DEBUG] Traceback: {traceback.format_exc()}")
                return f"Error creating customer record: {str(e)}"
            
            # Create the booking
            try:
                print(f"[DEBUG] Creating booking")
                booking = Booking.objects.create(
                    business=business,
                    lead=lead,
                    service_offering=service,
                    name=customer_name,
                    email=customer_email or '',
                    phone_number=customer_phone,
                    booking_date=date_obj,
                    start_time=time_obj,
                    end_time=(datetime.combine(date_obj, time_obj) + timedelta(minutes=service.duration)).time(),
                    status=BookingStatus.CONFIRMED,
                    notes=notes or ''
                )
                print(f"[DEBUG] Created booking: {booking.id}")
                
                # Add service items to the booking
                total_extra_duration = 0
                total_extra_price = Decimal('0.00')
                
                if service_items:
                    print(f"[DEBUG] Processing service items: {service_items}")
                    for item in service_items:
                        try:
                            identifier = item.get('identifier')
                            quantity = int(item.get('quantity', 1))
                            
                            if quantity <= 0:
                                print(f"[DEBUG] Invalid quantity for service item '{identifier}': {quantity}")
                                continue
                            
                            # Find service item by identifier
                            service_item = None
                            try:
                                # Try exact match first
                                service_item = ServiceItem.objects.get(
                                    business=business,
                                    identifier=identifier,
                                    is_active=True
                                )
                                print(f"[DEBUG] Found service item by exact identifier: {service_item.name} (ID: {service_item.id})")
                            except ServiceItem.DoesNotExist:
                                # Try case-insensitive match
                                service_item = ServiceItem.objects.filter(
                                    business=business,
                                    identifier__iexact=identifier,
                                    is_active=True
                                ).first()
                                
                                if service_item:
                                    print(f"[DEBUG] Found service item by case-insensitive identifier: {service_item.name} (ID: {service_item.id})")
                                else:
                                    # Try name match
                                    service_item = ServiceItem.objects.filter(
                                        business=business,
                                        name__iexact=identifier,
                                        is_active=True
                                    ).first()
                                    
                                    if service_item:
                                        print(f"[DEBUG] Found service item by name: {service_item.name} (ID: {service_item.id})")
                                    else:
                                        print(f"[DEBUG] Service item '{identifier}' not found")
                                        continue
                            
                            if service_item:
                                # Calculate price based on the service item's pricing rules
                                item_price = service_item.calculate_price(service.price, quantity)
                                
                                # Create the BookingServiceItem to link the booking with the service item
                                booking_service_item = BookingServiceItem.objects.create(
                                    booking=booking,
                                    service_item=service_item,
                                    quantity=quantity,
                                    price_at_booking=item_price
                                )
                                
                                # Add to total extra duration and price
                                total_extra_duration += service_item.duration_minutes * quantity
                                total_extra_price += item_price
                                
                                print(f"[DEBUG] Created booking service item: {booking_service_item.id}, Price: {item_price}, Extra Duration: {service_item.duration_minutes * quantity} minutes")
                        except Exception as e:
                            import traceback
                            print(f"[DEBUG] Error creating booking service item: {str(e)}")
                            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
                            continue
                else:
                    # Just add the main service without any additional service items
                    print(f"[DEBUG] No service items provided, just using the main service")
                    
                    # No additional service items, so no extra duration or price
                    pass
                
                # Update booking end time if there's extra duration
                if total_extra_duration > 0:
                    new_end_time = (datetime.combine(date_obj, time_obj) + 
                                   timedelta(minutes=service.duration + total_extra_duration)).time()
                    booking.end_time = new_end_time
                    booking.save(update_fields=['end_time'])
                    print(f"[DEBUG] Updated booking end time to include extra duration: {new_end_time}")
                
                # Assign staff members based on availability
                try:
                    print(f"[DEBUG] Finding available staff")
                    
                    # Get all staff for this business
                    all_staff = StaffMember.objects.filter(
                        business=business,
                        is_active=True
                    )
                    
                    print(f"[DEBUG] Total staff members: {all_staff.count()}")
                    
                    # Check availability for each staff member
                    available_staff = []
                    for staff in all_staff:
                        # Use the is_staff_available function from availability.py
                        from bookings.availability import is_staff_available
                        if is_staff_available(staff, date_obj, time_obj, booking.end_time):
                            available_staff.append(staff)
                            print(f"[DEBUG] Staff {staff.id} is available")
                    
                    print(f"[DEBUG] Found {len(available_staff)} available staff members")
                    
                    if available_staff:
                        # Assign the first available staff member
                        staff = available_staff[0]
                        BookingStaffAssignment.objects.create(
                            booking=booking,
                            staff_member=staff
                        )
                        staff_name = staff.get_full_name()
                        print(f"[DEBUG] Assigned staff: {staff_name}")
                    else:
                        # If no staff is available, assign the first staff member anyway
                        if all_staff.exists():
                            staff = all_staff.first()
                            BookingStaffAssignment.objects.create(
                                booking=booking,
                                staff_member=staff
                            )
                            staff_name = staff.get_full_name()
                            print(f"[DEBUG] No available staff found, assigned first staff: {staff_name}")
                        else:
                            staff_name = "No staff assigned yet"
                            print(f"[DEBUG] No staff assigned")
                except Exception as e:
                    import traceback
                    print(f"[DEBUG] Error assigning staff: {str(e)}")
                    print(f"[DEBUG] Traceback: {traceback.format_exc()}")
                    staff_name = "No staff assigned yet"
            
                # Create a detailed response with service items information
                response = f"Appointment booked successfully!\n\nDetails:\n- Date: {date}\n- Time: {time}\n- Service: {service.name}\n- Base Duration: {service.duration} minutes\n- Base Price: ${service.price}"
                
                # Add service items details if any were added
                booking_service_items = BookingServiceItem.objects.filter(booking=booking)
                if booking_service_items.exists():
                    response += "\n\nSelected Service Items:"
                    total_price = service.price
                    for bsi in booking_service_items:
                        response += f"\n- {bsi.service_item.name} (x{bsi.quantity}): ${bsi.price_at_booking}"
                        total_price += bsi.price_at_booking
                    
                    # Add total duration and price
                    total_duration = service.duration + total_extra_duration
                    response += f"\n\nTotal Duration: {total_duration} minutes"
                    response += f"\nTotal Price: ${total_price}"
                
                response += f"\nStaff: {staff_name}\n\nBooking ID: {booking.id}"
                
                return response
            
            except Exception as e:
                import traceback
                print(f"[DEBUG] Error in BookAppointmentTool: {str(e)}")
                print(f"[DEBUG] Traceback: {traceback.format_exc()}")
                return f"An error occurred while booking the appointment: {str(e)}"
            
        except Exception as e:
            import traceback
            print(f"[DEBUG] Error in BookAppointmentTool: {str(e)}")
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return f"An error occurred while booking the appointment: {str(e)}"

class RescheduleAppointmentInput(BaseModel):
    """Input for rescheduling an appointment."""
    booking_id: str = Field(..., description="ID of the booking to reschedule")
    new_date: str = Field(..., description="The new date for the appointment in format YYYY-MM-DD")
    new_time: str = Field(..., description="The new time for the appointment in format HH:MM")
    business_id: str = Field(..., description="ID of the business")

class RescheduleAppointmentTool(BaseTool):
    name: str = "reschedule_appointment"
    description: str = "Reschedule an existing appointment to a new date and time"
    args_schema: Type[BaseModel] = RescheduleAppointmentInput
    
    def _run(self, booking_id: str, new_date: str, new_time: str, business_id: str) -> str:
        try:
            # Parse the date and time
            try:
                new_booking_date = datetime.strptime(new_date, "%Y-%m-%d").date()
                new_booking_time = datetime.strptime(new_time, "%H:%M").time()
            except ValueError:
                return "Invalid date or time format. Please use YYYY-MM-DD for date and HH:MM for time."
            
            # Get the business
            try:
                business = Business.objects.get(id=business_id)
            except Business.DoesNotExist:
                return f"Business with ID {business_id} not found."
            
            # Get the booking
            try:
                booking = Booking.objects.get(id=booking_id, business=business)
            except Booking.DoesNotExist:
                return f"Booking with ID {booking_id} not found for this business."
            
            # Check if booking can be rescheduled
            if booking.status in [BookingStatus.CANCELLED, BookingStatus.COMPLETED, BookingStatus.NO_SHOW]:
                return f"Cannot reschedule a booking with status {booking.get_status_display()}."
            
            # Get service offering and duration
            service_offering = booking.service_offering
            duration_minutes = service_offering.duration if service_offering else 60
            
            # Check availability using the existing function
            try:
                # Create a datetime object for the new appointment time
                tz = pytz.UTC
                new_appointment_datetime = tz.localize(
                    datetime.combine(new_booking_date, new_booking_time)
                )
                
                # Check availability
                is_available, reason, _available_staff = check_timeslot_availability(
                    business=business,
                    start_time=new_appointment_datetime,
                    duration_minutes=duration_minutes,
                    service=service_offering
                )
                
                if not is_available:
                    # Find alternative slots
                    try:
                        alternative_slots = find_available_slots_on_date(
                            business_id=business.id,
                            date=new_booking_date,
                            duration_minutes=duration_minutes,
                            service_offering_id=service_offering.id if service_offering else None
                        )
                        
                        if alternative_slots:
                            alt_slots_text = ", ".join([f"{slot['time']}" for slot in alternative_slots[:3]])
                            return f"Cannot reschedule to {new_date} at {new_time}. Reason: {reason}. Alternative times: {alt_slots_text}"
                        else:
                            return f"Cannot reschedule to {new_date} at {new_time}. Reason: {reason}. No alternative times available on this date."
                    except Exception as e:
                        print(f"[DEBUG] Error finding alternative slots: {str(e)}")
                        return f"Cannot reschedule to {new_date} at {new_time}. Reason: {reason}."
            except Exception as e:
                print(f"[DEBUG] Error checking availability: {str(e)}")
                return f"Error checking availability for the new time: {str(e)}"
            
            # Calculate new end time
            start_datetime = datetime.combine(new_booking_date, new_booking_time)
            end_datetime = start_datetime + timedelta(minutes=duration_minutes)
            new_booking_end_time = end_datetime.time()
            
            # Update booking
            booking.booking_date = new_booking_date
            booking.start_time = new_booking_time
            booking.end_time = new_booking_end_time
            booking.status = BookingStatus.RESCHEDULED
            booking.save()
            
            # Get available staff
            available_staff = StaffMember.objects.filter(
                business=business,
                is_active=True
            ).exclude(
                # Exclude staff with conflicting bookings
                id__in=BookingStaffAssignment.objects.filter(
                    booking__start_time__lt=end_datetime.time(),
                    booking__end_time__gt=new_booking_time,
                    booking__booking_date=new_booking_date,
                    booking__status__in=[BookingStatus.CONFIRMED, BookingStatus.PENDING, BookingStatus.RESCHEDULED]
                ).values_list('staff_member_id', flat=True)
            ).exclude(
                # Exclude staff with unavailability records (off days)
                id__in=StaffAvailability.objects.filter(
                    start_time__lt=end_datetime.time(),
                    end_time__gt=new_booking_time,
                    off_day=True
                ).values_list('staff_member_id', flat=True)
            )
            
            # Reassign staff if needed
            current_staff_assignments = booking.staff_assignments.all()
            current_staff_ids = set(assignment.staff_member.id for assignment in current_staff_assignments)
            available_staff_ids = set(staff.id for staff in available_staff)
            
            # If none of the current staff are available at the new time
            if not current_staff_ids.intersection(available_staff_ids):
                # Clear existing staff assignments
                current_staff_assignments.delete()
                
                # Assign new staff
                if available_staff.exists():
                    staff = available_staff.first()
                    
                    # Create staff assignment
                    BookingStaffAssignment.objects.create(
                        booking=booking,
                        staff_member=staff
                    )
                    
                    staff_name = staff.get_full_name()
                    print(f"[DEBUG] Assigned new staff: {staff_name}")
            
            return f"Appointment rescheduled successfully to {new_date} at {new_time}. Booking ID: {booking.id}"
            
        except Exception as e:
            return f"Error rescheduling appointment: {str(e)}"

class CancelAppointmentInput(BaseModel):
    """Input for canceling an appointment."""
    booking_id: str = Field(..., description="ID of the booking to cancel")
    business_id: str = Field(..., description="ID of the business")
    reason: Optional[str] = Field(None, description="Reason for cancellation")

class CancelAppointmentTool(BaseTool):
    name: str = "cancel_appointment"
    description: str = "Cancel an existing appointment"
    args_schema: Type[BaseModel] = CancelAppointmentInput
    
    def _run(self, booking_id: str, business_id: str, reason: Optional[str] = None) -> str:
        try:
            print(f"[DEBUG] CancelAppointmentTool called with: booking_id={booking_id}, business_id={business_id}, reason={reason}")
            
            # Get the business
            try:
                # Try to get by ID first
                try:
                    from uuid import UUID
                    # Check if business_id is a valid UUID
                    print(f"[DEBUG] Attempting to parse business_id as UUID: {business_id}")
                    uuid_obj = UUID(business_id, version=4)
                    business = Business.objects.get(id=uuid_obj)
                    print(f"[DEBUG] Found business by UUID: {business.name}")
                except (ValueError, TypeError) as e:
                    print(f"[DEBUG] business_id is not a valid UUID: {str(e)}")
                    # If not a valid UUID, try to find by name
                    print(f"[DEBUG] Trying to find business by name: {business_id}")
                    business = Business.objects.filter(name__iexact=business_id).first()
                    if not business:
                        print(f"[DEBUG] Business with name '{business_id}' not found")
                        return f"Business with name '{business_id}' not found. Please use a valid business ID."
                    print(f"[DEBUG] Found business by name: {business.name} (ID: {business.id})")
            except Business.DoesNotExist:
                print(f"[DEBUG] Business with ID {business_id} not found")
                return f"Business with ID {business_id} not found."
            
            # Get the booking
            try:
                print(f"[DEBUG] Looking for booking with ID: {booking_id}")
                booking = Booking.objects.get(id=booking_id, business=business)
                print(f"[DEBUG] Found booking: {booking.id}")
            except Booking.DoesNotExist:
                print(f"[DEBUG] Booking with ID {booking_id} not found")
                return f"Booking with ID {booking_id} not found for business {business.name}."
            
            # Check if booking is already cancelled
            if booking.status == BookingStatus.CANCELLED:
                print(f"[DEBUG] Booking is already cancelled")
                return f"This appointment is already cancelled."
            
            # Cancel the booking
            booking.status = BookingStatus.CANCELLED
            booking.cancellation_reason = reason or "Cancelled by customer"
            booking.save(update_fields=['status', 'cancellation_reason'])
            
            print(f"[DEBUG] Booking cancelled successfully")
            return f"Appointment cancelled successfully. Cancellation reason: {booking.cancellation_reason}"
            
        except Exception as e:
            import traceback
            print(f"[DEBUG] Error in CancelAppointmentTool: {str(e)}")
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return f"An error occurred while cancelling the appointment: {str(e)}"

class GetServiceItemsInput(BaseModel):
    """Input for getting available service items."""
    business_id: str = Field(..., description="ID of the business")
    service_name: Optional[str] = Field(None, description="Name of the service to filter items by")

class GetServiceItemsTool(BaseTool):
    name: str = "get_service_items"
    description: str = "Get available service items for a business"
    args_schema: Type[BaseModel] = GetServiceItemsInput
    
    def _run(self, business_id: str, service_name: Optional[str] = None) -> str:
        try:
            print(f"[DEBUG] GetServiceItemsTool called with: business_id={business_id}, service_name={service_name}")
            
            # Get the business
            try:
                # Try to get by ID first
                try:
                    from uuid import UUID
                    # Check if business_id is a valid UUID
                    print(f"[DEBUG] Attempting to parse business_id as UUID: {business_id}")
                    uuid_obj = UUID(business_id, version=4)
                    business = Business.objects.get(id=uuid_obj)
                    print(f"[DEBUG] Found business by UUID: {business.name}")
                except (ValueError, TypeError) as e:
                    print(f"[DEBUG] business_id is not a valid UUID: {str(e)}")
                    # If not a valid UUID, try to find by name
                    print(f"[DEBUG] Trying to find business by name: {business_id}")
                    business = Business.objects.filter(name__iexact=business_id).first()
                    if not business:
                        print(f"[DEBUG] Business with name '{business_id}' not found")
                        return f"Business with name '{business_id}' not found. Please use a valid business ID."
                    print(f"[DEBUG] Found business by name: {business.name} (ID: {business.id})")
            except Business.DoesNotExist:
                print(f"[DEBUG] Business with ID {business_id} not found")
                return f"Business with ID {business_id} not found."
            
            # Get service items
            service_items_query = ServiceItem.objects.filter(
                business=business,
                is_active=True
            )
            
            # Filter by service if provided
            if service_name:
                try:
                    service = ServiceOffering.objects.get(
                        business=business,
                        name__iexact=service_name,
                        is_active=True
                    )
                    
                    # We're not filtering by service offering anymore as requested
                    # Just keeping the service for reference in the response
                    
                except ServiceOffering.DoesNotExist:
                    print(f"[DEBUG] Service '{service_name}' not found")
                    return f"Service '{service_name}' not found for business '{business.name}'."
            
            service_items = service_items_query.all()
            
            if not service_items:
                return f"No service items found for business '{business.name}'" + \
                       (f" and service '{service_name}'" if service_name else "")
            
            # Format the response
            items_info = []
            for item in service_items:
                price_info = f"${item.price_value}" if item.price_type == 'fixed' else \
                             f"{item.price_value}% of base price" if item.price_type == 'percentage' else \
                             f"${item.price_value}/hour" if item.price_type == 'hourly' else \
                             f"${item.price_value} per unit"
                
                items_info.append({
                    "identifier": item.identifier,
                    "name": item.name,
                    "description": item.description or "No description",
                    "price": price_info,
                    "duration": f"{item.duration_minutes} minutes" if item.duration_minutes else "No additional time",
                    "optional": "Optional" if item.is_optional else "Required"
                })
            
            # Create a formatted response
            response = f"Available service items for {business.name}"
            if service_name:
                response += f" and service '{service_name}'"
            response += ":\n\n"
            
            for i, item in enumerate(items_info, 1):
                response += f"{i}. {item['name']} (ID: {item['identifier']})\n"
                response += f"   Description: {item['description']}\n"
                response += f"   Price: {item['price']}\n"
                response += f"   Duration: {item['duration']}\n"
                response += f"   {item['optional']}\n\n"
            
            return response
            
        except Exception as e:
            import traceback
            print(f"[DEBUG] Error in GetServiceItemsTool: {str(e)}")
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return f"An error occurred while getting service items: {str(e)}"