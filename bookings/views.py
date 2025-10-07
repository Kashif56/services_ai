from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db import models
from business.models import ServiceOffering, BusinessCustomField, ServiceItem, ServiceOfferingItem, Industry, IndustryField
from .models import Booking, BookingField, BookingServiceItem, BookingStatus, StaffMember, BookingStaffAssignment
from leads.models import Lead
from django.utils import timezone
import json
import datetime
from decimal import Decimal
from .availability import check_timeslot_availability
from business.utils import get_user_business

# Create your views here.
@login_required
def index(request):
    business = getattr(request.user, 'business', None)
    if not business:
        messages.error(request, 'Please register your business first.')
        return redirect('business:register')
    
    # Get all bookings for this business
    bookings = Booking.objects.filter(business=business).order_by('-created_at')
    
    # Get status filter if provided
    status_filter = request.GET.get('status', '')
    if status_filter and status_filter in dict(BookingStatus.choices):
        bookings = bookings.filter(status=status_filter)
    
    # Get date range filter if provided
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        try:
            bookings = bookings.filter(booking_date__gte=date_from)
        except ValueError:
            pass
    if date_to:
        try:
            bookings = bookings.filter(booking_date__lte=date_to)
        except ValueError:
            pass
    
    # Get search query if provided
    search_query = request.GET.get('search', '')
    if search_query:
        bookings = bookings.filter(
            models.Q(name__icontains=search_query) |
            models.Q(email__icontains=search_query) |
            models.Q(phone_number__icontains=search_query) |
            models.Q(location_details__icontains=search_query) |
            models.Q(notes__icontains=search_query)
        )
    
    return render(request, 'bookings/index.html', {
        'title': 'Bookings',
        'bookings': bookings,
        'booking_statuses': BookingStatus.choices,
        'current_status': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query
    })

@login_required
def create_booking(request):
    business = getattr(request.user, 'business', None)
    if not business:
        messages.error(request, 'Please register your business first.')
        return redirect('business:register')

    service_offerings = ServiceOffering.objects.filter(business=business, is_active=True).order_by('name')
    custom_fields = BusinessCustomField.objects.filter(business=business, is_active=True).order_by('display_order', 'name')
    
    # Check if a lead ID was provided in the URL
    lead_id = request.GET.get('lead')
    selected_lead = None
    
    if lead_id:
        try:
            selected_lead = Lead.objects.get(id=lead_id, business=business)
        except Lead.DoesNotExist:
            pass

    if request.method == 'POST':
        # Basic Booking fields
        service_type_id = request.POST.get('service_type')
        booking_date = request.POST.get('booking_date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        location_type = request.POST.get('location_type')
        location_details = request.POST.get('location_details')
        notes = request.POST.get('notes')
        staff_member_id = request.POST.get('staff_member_id')
        
        # Client information
        client_name = request.POST.get('client_name')
        client_email = request.POST.get('client_email')
        client_phone = request.POST.get('client_phone')
        selected_lead_id = request.POST.get('lead_id')

        # Validation (minimal, expand as needed)
        errors = []
        if not service_type_id:
            errors.append('Service type is required.')
        if not booking_date:
            errors.append('Booking date is required.')
        if not start_time or not end_time:
            errors.append('Start and end time are required.')
        if not client_name:
            errors.append('Client name is required.')
        if not client_email:
            errors.append('Client email is required.')
        if not client_phone:
            errors.append('Client phone is required.')
        if not staff_member_id:
            errors.append('Staff member selection is required.')
            
        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'bookings/create_booking.html', {
                'service_offerings': service_offerings,
                'custom_fields': custom_fields,
            })

        try:
            service_offering = ServiceOffering.objects.get(id=service_type_id, business=business)
        except ServiceOffering.DoesNotExist:
            messages.error(request, 'Invalid service selected.')
            return render(request, 'bookings/create_booking.html', {
                'service_offerings': service_offerings,
                'custom_fields': custom_fields,
            })

        # Get the lead if selected
        lead = None
        if selected_lead_id:
            try:
                lead = Lead.objects.get(id=selected_lead_id, business=business)
                # Update lead status to appointment_scheduled
                lead.status = 'appointment_scheduled'
                lead.save()
            except Lead.DoesNotExist:
                pass
        
        # Create Booking
        booking = Booking.objects.create(
            business=business,
            lead=lead,  # This can be None if no lead was selected
            service_offering=service_offering,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            location_type=location_type,
            location_details=location_details,
            notes=notes,
            status='pending',
            name=client_name,
            email=client_email,
            phone_number=client_phone
        )

        # Create staff assignment
        try:
            staff_member = StaffMember.objects.get(id=staff_member_id, business=business)
            BookingStaffAssignment.objects.create(
                booking=booking,
                staff_member=staff_member,
                is_primary=True
            )
        except StaffMember.DoesNotExist:
            # If staff member doesn't exist, delete the booking and show error
            booking.delete()
            messages.error(request, 'Selected staff member not found.')
            return render(request, 'bookings/create_booking.html', {
                'service_offerings': service_offerings,
                'custom_fields': custom_fields,
            })

        # Save custom fields
        for field in custom_fields:
            val = request.POST.get(f'custom_{field.slug}', '')
            if field.required and not val and field.field_type != 'boolean':
                messages.error(request, f'{field.name} is required.')
                booking.delete()
                return render(request, 'bookings/create_booking.html', {
                    'service_offerings': service_offerings,
                    'custom_fields': custom_fields,
                })
                
            # Handle boolean fields (checkboxes) properly
            if field.field_type == 'boolean':
                val = 'true' if request.POST.get(f'custom_{field.slug}') else 'false'
                
            BookingField.objects.create(
                booking=booking,
                field_type='business',
                business_field=field,
                value=val,
            )
        
        # We're not processing industry fields as requested
        
        # Save service items
        service_items = request.POST.getlist('service_items[]')
        selected_items_data = {}
        
        print("=== BOOKING CREATION - SERVICE ITEMS ===")
        print("Service items:", service_items)
        
        # Check if we have the JSON data for selected items
        if request.POST.get('selected_items_data'):
            try:
                selected_items_data = json.loads(request.POST.get('selected_items_data'))
                print("Selected items data (parsed):", selected_items_data)
                for item_id, item_data in selected_items_data.items():
                    print(f"  Item {item_id}: value='{item_data.get('value')}', quantity={item_data.get('quantity')}")
            except json.JSONDecodeError as e:
                # If JSON is invalid, continue with empty dict
                print(f"ERROR: Failed to parse selected_items_data JSON: {e}")
                pass
        
        # Combine service_items list with any additional items in selected_items_data
        # This ensures we process all items that have values, even if they weren't checked
        all_service_items = set(service_items)
        for item_id in selected_items_data.keys():
            if item_id not in all_service_items and selected_items_data[item_id].get('value'):
                all_service_items.add(item_id)
        
        print("All service items to process:", all_service_items)
        
        for item_id in all_service_items:
            try:
                service_item = ServiceItem.objects.get(id=item_id, business=business)
                
                # Get quantity and field value from the selected_items_data
                quantity = 1
                field_value = ''
                
                if item_id in selected_items_data:
                    item_data = selected_items_data[item_id]
                    
                    # For non-free items with field_type='number', use the field value as the quantity
                    # since we're displaying only one input field in the UI
                    if service_item.price_type != 'free' and service_item.field_type == 'number':
                        # If there's a value, use it as the quantity
                        if 'value' in item_data and item_data['value']:
                            try:
                                quantity = int(float(item_data['value']))
                                # Store the same value as field_value for consistency
                                field_value = str(quantity)
                            except (ValueError, TypeError):
                                # If conversion fails, keep default quantity
                                pass
                    else:
                        # For all other cases, use the standard quantity field
                        quantity = int(item_data.get('quantity', 1))
                        field_value = item_data.get('value', '')
                else:
                    # Fallback to the old method if JSON data is not available
                    quantity = int(request.POST.get(f'item_quantity_{item_id}', 1))
                
                # Calculate price at booking time
                # For select/boolean fields with option pricing, pass the selected value
                price_at_booking = service_item.calculate_price(
                    base_price=service_offering.price, 
                    quantity=quantity,
                    selected_value=field_value if service_item.field_type in ['select', 'boolean'] else None
                )

                print(f"  Processing item {item_id} ({service_item.name}):")
                print(f"    Field type: {service_item.field_type}, Price type: {service_item.price_type}")
                print(f"    Field value to save: '{field_value}'")
                print(f"    Quantity: {quantity}, Price at booking: {price_at_booking}")
                
                # Create the booking service item
                booking_service_item = BookingServiceItem.objects.create(
                    booking=booking,
                    service_item=service_item,
                    quantity=quantity,
                    price_at_booking=price_at_booking
                )
                
                # Set the appropriate field value based on field type
                booking_service_item.set_response_value(field_value)
                booking_service_item.save()
                
                print(f"    Saved - select_value: '{booking_service_item.select_value}', "
                      f"boolean_value: {booking_service_item.boolean_value}")
            except (ServiceItem.DoesNotExist, ValueError):
                # Log this but don't fail the booking
                pass

        messages.success(request, 'Booking created successfully!')
        return redirect(reverse('bookings:index'))

    # GET
    return render(request, 'bookings/create_booking.html', {
        'service_offerings': service_offerings,
        'custom_fields': custom_fields,
        'selected_lead': selected_lead,
    })

@login_required
def edit_booking(request, booking_id):
    """Edit an existing booking"""
    business = getattr(request.user, 'business', None)
    if not business:
        messages.error(request, 'Please register your business first.')
        return redirect('business:register')
    
    # Get the booking
    try:
        booking = Booking.objects.select_related(
            'service_offering', 
            'lead'
        ).prefetch_related(
            'fields',
            'fields__business_field',
            'service_items',
            'service_items__service_item',
            'staff_assignments',
            'staff_assignments__staff_member'
        ).get(id=booking_id, business=business)
    except Booking.DoesNotExist:
        messages.error(request, 'Booking not found.')
        return redirect('bookings:index')
    
    service_offerings = ServiceOffering.objects.filter(business=business, is_active=True).order_by('name')
    custom_fields = BusinessCustomField.objects.filter(business=business, is_active=True).order_by('display_order', 'name')
    
    if request.method == 'POST':
        # Basic Booking fields
        service_type_id = request.POST.get('service_type')
        booking_date = request.POST.get('booking_date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        location_type = request.POST.get('location_type')
        location_details = request.POST.get('location_details')
        notes = request.POST.get('notes')
        staff_member_id = request.POST.get('staff_member_id')
        
        # Debug: Print received date/time values
        print(f"=== EDIT BOOKING POST DATA ===")
        print(f"Booking Date: {booking_date}")
        print(f"Start Time: {start_time}")
        print(f"End Time: {end_time}")
        
        # Client information
        client_name = request.POST.get('client_name')
        client_email = request.POST.get('client_email')
        client_phone = request.POST.get('client_phone')
        selected_lead_id = request.POST.get('lead_id')

        # Validation
        errors = []
        if not service_type_id:
            errors.append('Service type is required.')
        if not booking_date:
            errors.append('Booking date is required.')
        if not start_time or not end_time:
            errors.append('Start and end time are required.')
        if not client_name:
            errors.append('Client name is required.')
        if not client_email:
            errors.append('Client email is required.')
        if not client_phone:
            errors.append('Client phone is required.')
        if not staff_member_id:
            errors.append('Staff member selection is required.')
            
        if errors:
            for err in errors:
                messages.error(request, err)
            return redirect('bookings:edit_booking', booking_id=booking_id)

        try:
            service_offering = ServiceOffering.objects.get(id=service_type_id, business=business)
        except ServiceOffering.DoesNotExist:
            messages.error(request, 'Invalid service selected.')
            return redirect('bookings:edit_booking', booking_id=booking_id)

        # Get the lead if selected
        lead = None
        if selected_lead_id:
            try:
                lead = Lead.objects.get(id=selected_lead_id, business=business)
            except Lead.DoesNotExist:
                pass
        
        # Update Booking
        booking.lead = lead
        booking.service_offering = service_offering
        booking.booking_date = booking_date
        booking.start_time = start_time
        booking.end_time = end_time
        booking.location_type = location_type
        booking.location_details = location_details
        booking.notes = notes
        booking.name = client_name
        booking.email = client_email
        booking.phone_number = client_phone
        booking.save()
        
        # Debug: Confirm saved values
        print(f"=== BOOKING SAVED ===")
        print(f"Saved Booking Date: {booking.booking_date}")
        print(f"Saved Start Time: {booking.start_time}")
        print(f"Saved End Time: {booking.end_time}")

        # Update staff assignment
        try:
            staff_member = StaffMember.objects.get(id=staff_member_id, business=business)
            # Delete existing staff assignments
            BookingStaffAssignment.objects.filter(booking=booking).delete()
            # Create new staff assignment
            BookingStaffAssignment.objects.create(
                booking=booking,
                staff_member=staff_member,
                is_primary=True
            )
        except StaffMember.DoesNotExist:
            messages.error(request, 'Selected staff member not found.')
            return redirect('bookings:edit_booking', booking_id=booking_id)

        # Update custom fields
        # Delete existing custom fields
        BookingField.objects.filter(booking=booking).delete()
        
        for field in custom_fields:
            val = request.POST.get(f'custom_{field.slug}', '')
            if field.required and not val and field.field_type != 'boolean':
                messages.error(request, f'{field.name} is required.')
                return redirect('bookings:edit_booking', booking_id=booking_id)
                
            # Handle boolean fields (checkboxes) properly
            if field.field_type == 'boolean':
                val = 'true' if request.POST.get(f'custom_{field.slug}') else 'false'
                
            BookingField.objects.create(
                booking=booking,
                field_type='business',
                business_field=field,
                value=val,
            )
        
        # Update service items
        # Delete existing service items
        BookingServiceItem.objects.filter(booking=booking).delete()
        
        service_items = request.POST.getlist('service_items[]')
        selected_items_data = {}
        
        print("=== EDIT BOOKING - SERVICE ITEMS ===")
        print("Service items:", service_items)
        
        # Check if we have the JSON data for selected items
        if request.POST.get('selected_items_data'):
            try:
                selected_items_data = json.loads(request.POST.get('selected_items_data'))
                print("Selected items data (parsed):", selected_items_data)
                for item_id, item_data in selected_items_data.items():
                    print(f"  Item {item_id}: value='{item_data.get('value')}', quantity={item_data.get('quantity')}")
            except json.JSONDecodeError as e:
                print(f"ERROR: Failed to parse selected_items_data JSON: {e}")
                pass
        
        # Combine service_items list with any additional items in selected_items_data
        all_service_items = set(service_items)
        for item_id in selected_items_data.keys():
            if item_id not in all_service_items and selected_items_data[item_id].get('value'):
                all_service_items.add(item_id)
        
        print(f"All service items to process: {all_service_items}")
        
        for item_id in all_service_items:
            try:
                service_item = ServiceItem.objects.get(id=item_id, business=business)
                
                # Get quantity and field value from the selected_items_data
                quantity = 1
                field_value = ''
                
                if item_id in selected_items_data:
                    item_data = selected_items_data[item_id]
                    
                    # For non-free items with field_type='number', use the field value as the quantity
                    if service_item.price_type != 'free' and service_item.field_type == 'number':
                        if 'value' in item_data and item_data['value']:
                            try:
                                quantity = int(float(item_data['value']))
                                field_value = str(quantity)
                            except (ValueError, TypeError):
                                pass
                    else:
                        quantity = int(item_data.get('quantity', 1))
                        field_value = item_data.get('value', '')
                else:
                    quantity = int(request.POST.get(f'item_quantity_{item_id}', 1))
                
                # Calculate price at booking time
                # For select/boolean fields with option pricing, pass the selected value
                price_at_booking = service_item.calculate_price(
                    base_price=service_offering.price, 
                    quantity=quantity,
                    selected_value=field_value if service_item.field_type in ['select', 'boolean'] else None
                )
                
                print(f"  Processing item {item_id} ({service_item.name}):")
                print(f"    Field type: {service_item.field_type}, Price type: {service_item.price_type}")
                print(f"    Field value to save: '{field_value}'")
                print(f"    Quantity: {quantity}, Price at booking: {price_at_booking}")
                
                # Create the booking service item
                booking_service_item = BookingServiceItem.objects.create(
                    booking=booking,
                    service_item=service_item,
                    quantity=quantity,
                    price_at_booking=price_at_booking
                )
                
                # Set the appropriate field value based on field type
                booking_service_item.set_response_value(field_value)
                booking_service_item.save()
                
                print(f"    Saved - select_value: '{booking_service_item.select_value}', "
                      f"boolean_value: {booking_service_item.boolean_value}")
            except (ServiceItem.DoesNotExist, ValueError):
                pass

        messages.success(request, 'Booking updated successfully!')
        return redirect(reverse('bookings:booking_detail', kwargs={'booking_id': booking_id}))

    # GET - Prepare data for the form
    # Get booking fields data
    booking_fields_data = {}
    for booking_field in booking.fields.all():
        if booking_field.business_field:
            booking_fields_data[f'custom_{booking_field.business_field.slug}'] = booking_field.value
    
    # Get booking service items data
    booking_service_items = []
    for bsi in booking.service_items.all():
        response_value = bsi.get_response_value()
        # Convert Decimal to string for JSON serialization
        if isinstance(response_value, Decimal):
            response_value = str(response_value)
        
        booking_service_items.append({
            'id': str(bsi.service_item.id),
            'quantity': bsi.quantity,
            'response_value': response_value if response_value else ''
        })
    
    # Get staff assignment
    staff_assignment = booking.staff_assignments.filter(is_primary=True).first()
    
    # Convert to JSON with proper encoding
    booking_fields_data_json = json.dumps(booking_fields_data) if booking_fields_data else '{}'
    booking_service_items_json = json.dumps(booking_service_items) if booking_service_items else '[]'
    
    return render(request, 'bookings/edit_booking.html', {
        'booking': booking,
        'service_offerings': service_offerings,
        'custom_fields': custom_fields,
        'booking_fields_data_json': booking_fields_data_json,
        'booking_service_items_json': booking_service_items_json,
        'staff_assignment': staff_assignment,
    })

@login_required
def booking_detail(request, booking_id):
    """View for displaying detailed information about a booking"""

    
    business = get_user_business(request.user)
    if not business:
        messages.error(request, 'Please register your business first.')
        return redirect('business:register')
    
    try:
        # Get the booking with all related data
        booking = Booking.objects.select_related(
            'business', 
            'service_offering',
            'lead'
        ).prefetch_related(
            'fields',
            'fields__business_field',
            'fields__industry_field',
            'service_items',
            'service_items__service_item',
            'staff_assignments',
            'staff_assignments__staff_member',
            'reminders'
        ).get(id=booking_id, business=business)
        
        # Get custom fields
        business_fields = BookingField.objects.filter(
            booking=booking,
            business_field__isnull=False
        ).select_related('business_field')
        
        industry_fields = BookingField.objects.filter(
            booking=booking,
            industry_field__isnull=False
        ).select_related('industry_field')
        
        # Get service items
        service_items = booking.service_items.all()
        
        print(f"=== BOOKING DETAIL - PRICE CALCULATION ===")
        print(f"Booking ID: {booking_id}")
        print(f"Base service price: {booking.service_offering.price}")
        
        # Separate free and paid service items
        paid_service_items = []
        free_service_items = []
        for item in service_items:
            print(f"Item: {item.service_item.name}, price_at_booking: {item.price_at_booking}, "
                  f"field_type: {item.service_item.field_type}, boolean_value: {item.boolean_value}")
            if item.service_item.price_type == 'free':
                free_service_items.append(item)
            else:
                paid_service_items.append(item)
        
        # Calculate paid service items total
        paid_service_items_total = sum(item.price_at_booking for item in paid_service_items)
        
        print(f"Paid service items total: {paid_service_items_total}")
        
        # Check if there are any paid items
        has_paid_items = len(paid_service_items) > 0
        
        # Calculate total price (base price + paid items only)
        total_price = booking.service_offering.price + paid_service_items_total
        
        print(f"Total price: {total_price}")
        
        # Get booking events for timeline (only show enabled event types)
        from .models import BookingEvent, BookingEventType
        booking_events = booking.events.select_related('event_type').filter(
            event_type__show_in_timeline=True
        ).order_by('-created_at')
        
        # Build timeline from events
        timeline = []
        
        for event in booking_events:
            timeline_item = {
                'event_type': event.event_type.event_key,
                'event_name': event.event_type.name,
                'timestamp': event.created_at,
                'type': event.event_type.color,
                'icon': event.event_type.icon,
                'description': event.description,
                'reason': event.reason
            }
            
            # Add reschedule details if applicable
            if event.event_type.event_key == 'rescheduled' and event.old_date:
                timeline_item['old_datetime'] = f"{event.old_date} {event.old_start_time.strftime('%I:%M %p') if event.old_start_time else ''}"
                timeline_item['new_datetime'] = f"{event.new_date} {event.new_start_time.strftime('%I:%M %p') if event.new_start_time else ''}"
            
            timeline.append(timeline_item)
        
        # Get enabled event types for action buttons
        enabled_event_types = BookingEventType.objects.filter(
            business=business,
            is_enabled=True
        ).order_by('display_order')
        
        # Get enabled reminder types
        from .models import ReminderType
        enabled_reminder_types = ReminderType.objects.filter(
            business=business,
            is_enabled=True
        ).order_by('display_order')
        
        # Get invoice and payment information
        from invoices.models import Invoice, Payment
        invoice = Invoice.objects.filter(booking=booking).first()
        payments = []
        total_paid = 0
        balance_due = total_price
        
        if invoice:
            payments = Payment.objects.filter(invoice=invoice).order_by('-payment_date')
            total_paid = sum(payment.amount for payment in payments if not payment.is_refunded)
            balance_due = total_price - total_paid
        
        return render(request, 'bookings/booking_detail.html', {
            'title': f'Booking: {booking.name}',
            'booking': booking,
            'business_fields': business_fields,
            'industry_fields': industry_fields,
            'service_items': service_items,
            'free_service_items': free_service_items,
            'paid_service_items': paid_service_items,
            'paid_service_items_total': paid_service_items_total,
            'has_paid_items': has_paid_items,
            'total_price': total_price,
            'timeline': timeline,
            'enabled_event_types': enabled_event_types,
            'enabled_reminder_types': enabled_reminder_types,
            'invoice': invoice,
            'payments': payments,
            'total_paid': total_paid,
            'balance_due': balance_due,
            'duration': booking.get_service_duration()
        })
       
    except Booking.DoesNotExist:
        messages.error(request, 'Booking not found.')
        return redirect('bookings:index')

@login_required
def get_service_items(request, service_id):
    """API endpoint to get service items filtered by service offering"""
    business = getattr(request.user, 'business', None)
    if not business:
        return JsonResponse({'error': 'Business not found'}, status=404)
    
    try:
        # Get the service offering for reference
        service_offering = ServiceOffering.objects.get(id=service_id, business=business)
        
        # Get service items linked to this specific service offering
        service_items = ServiceItem.objects.filter(
            business=business, 
            service_offering=service_offering,
            is_active=True
        )
        
        items = []
        for service_item in service_items:
            # Check if this item is required for the selected service
            is_required = ServiceOfferingItem.objects.filter(
                service_offering=service_offering,
                service_item=service_item,
                is_required=True
            ).exists()
            
            items.append({
                'id': str(service_item.id),
                'name': service_item.name,
                'description': service_item.description,
                'price_type': service_item.price_type,
                'price_value': float(service_item.price_value),
                'field_type': service_item.field_type,
                'field_options': service_item.field_options,
                'option_pricing': service_item.option_pricing,
                'is_required': is_required,
                'is_optional': service_item.is_optional,
                'max_quantity': service_item.max_quantity,
                'duration_minutes': service_item.duration_minutes
            })
        
        return JsonResponse({
            'service_id': str(service_id),
            'service_name': service_offering.name,
            'items': items
        })
    except ServiceOffering.DoesNotExist:
        return JsonResponse({'error': 'Service not found'}, status=404)


@login_required
def get_leads(request):
    """API endpoint to get leads for the booking form"""
    business = getattr(request.user, 'business', None)
    if not business:
        return JsonResponse({'error': 'Business not found'}, status=404)
    
    # Check if a specific lead ID was requested
    lead_id = request.GET.get('lead_id')
    
    if lead_id:
        # Return only the specific lead if it exists and belongs to the business
        try:
            lead = Lead.objects.get(id=lead_id, business=business)
            lead_data = [{
                'id': str(lead.id),
                'name': f"{lead.first_name} {lead.last_name}",
                'email': lead.email,
                'phone': lead.phone,
                'status': lead.status,
                'source': lead.source
            }]
            return JsonResponse({'leads': lead_data})
        except Lead.DoesNotExist:
            return JsonResponse({'error': 'Lead not found'}, status=404)
    else:
        # Return all leads for the business
        leads = Lead.objects.filter(business=business).order_by('-created_at')
        lead_data = [{
            'id': str(lead.id),
            'name': f"{lead.first_name} {lead.last_name}",
            'email': lead.email,
            'phone': lead.phone,
            'status': lead.status,
            'source': lead.source
        } for lead in leads]
        return JsonResponse({'leads': lead_data})

@login_required
def check_availability(request):
    """
    API endpoint to check if a timeslot is available for booking
    and provide alternate timeslots if not available.
    
    Required parameters:
    - date: Date string in format 'YYYY-MM-DD'
    - time: Time string in format 'HH:MM'
    
    Optional parameters:
    - duration_minutes: Duration of the appointment in minutes (default: 60)
    - service_offering_id: ID of the service offering
    - staff_member_id: ID of a specific staff member to check
    """
    business = getattr(request.user, 'business', None)
    if not business:
        return JsonResponse({'error': 'Business not found'}, status=404)
    
    # Get parameters from request
    date_str = request.GET.get('date')
    time_str = request.GET.get('time')
    duration_minutes = request.GET.get('duration_minutes', 60)
    service_offering_id = request.GET.get('service_offering_id')
    staff_member_id = request.GET.get('staff_member_id')

    print(request.GET)
    
    # Validate required parameters
    if not date_str or not time_str:
        return JsonResponse({'error': 'Date and time are required parameters'}, status=400)
    
    try:
        duration_minutes = int(duration_minutes)
    except ValueError:
        return JsonResponse({'error': 'Duration must be a valid integer'}, status=400)
    from datetime import datetime
    # Convert date and time strings to datetime object
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        time_obj = datetime.strptime(time_str, '%H:%M').time()
        start_time = datetime.combine(date_obj, time_obj)
    except ValueError:
        return JsonResponse({'error': 'Invalid date or time format'}, status=400)
    
    # Get service object if ID is provided
    service = None
    if service_offering_id:
        try:
            service = ServiceOffering.objects.get(id=service_offering_id, business=business)
        except ServiceOffering.DoesNotExist:
            pass  # Service will remain None
    
    # Check availability
    is_available, reason, available_staff = check_timeslot_availability(
        business.id,
        start_time,
        duration_minutes,
        service
    )
    
    availability_result = {
        'is_available': is_available,
        'reason': reason if not is_available else None,
        'available_staff': available_staff
    }
    
    # If not available, get alternate timeslots
    if not is_available:
        from .availability import get_alternate_timeslots
        alternate_slots = get_alternate_timeslots(
            business.id,
            date_obj,
            time_obj,
            duration_minutes,
            service_offering_id,
            staff_member_id
        )
        availability_result['alternate_slots'] = alternate_slots

    print("Availability result:", availability_result)
    
    return JsonResponse(availability_result)

@login_required
@require_http_methods(["POST"])
def cancel_booking(request, booking_id):
    """
    Cancel a booking with reason
    """
    business = get_user_business(request.user)
    if not business:
        return JsonResponse({'success': False, 'message': 'Business not found'}, status=404)
    
    try:
        booking = Booking.objects.get(id=booking_id, business=business)
        
        # Check if booking can be cancelled (must be at least 24 hours before appointment)
        from datetime import datetime, timedelta
        booking_datetime = timezone.make_aware(datetime.combine(booking.booking_date, booking.start_time))
        now = timezone.now()
        hours_until_booking = (booking_datetime - now).total_seconds() / 3600
        
        if hours_until_booking < 24:
            return JsonResponse({
                'success': False,
                'message': 'Cannot cancel booking less than 24 hours before appointment time'
            }, status=400)
        
        # Get cancellation reason from request
        data = json.loads(request.body)
        reason = data.get('reason', '')
        
        if not reason:
            return JsonResponse({
                'success': False,
                'message': 'Cancellation reason is required'
            }, status=400)
        
        # Update booking status
        booking.status = BookingStatus.CANCELLED
        booking.cancellation_reason = reason
        booking.save()
        
        # Create booking event
        from .models import BookingEvent, BookingEventType
        cancelled_event_type = BookingEventType.objects.filter(
            business=business,
            event_key='cancelled',
            is_enabled=True
        ).first()
        
        if cancelled_event_type:
            BookingEvent.objects.create(
                booking=booking,
                event_type=cancelled_event_type,
                description=f'Booking cancelled',
                reason=reason
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Booking cancelled successfully'
        })
        
    except Booking.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Booking not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
def get_available_timeslots(request, booking_id):
    """
    Get available timeslots for a specific date for rescheduling
    """
    business = get_user_business(request.user)
    if not business:
        return JsonResponse({'success': False, 'message': 'Business not found'}, status=404)
    
    try:
        booking = Booking.objects.get(id=booking_id, business=business)
        
        # Get date from request
        date_str = request.GET.get('date')
        if not date_str:
            return JsonResponse({'success': False, 'message': 'Date is required'}, status=400)
        
        from datetime import datetime, timedelta
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get booking duration
        duration_minutes = booking.get_service_duration()
        
        # Get assigned staff member
        staff_assignment = booking.staff_assignments.first()
        if not staff_assignment:
            return JsonResponse({'success': False, 'message': 'No staff assigned to booking'}, status=400)
        
        staff_member = staff_assignment.staff_member
        
        # Get staff availability for the selected date
        from .models import StaffAvailability, AVAILABILITY_TYPE, WEEKDAY_CHOICES
        
        weekday = date_obj.weekday()
        
        # Check for specific date availability/unavailability first
        specific_availabilities = StaffAvailability.objects.filter(
            staff_member=staff_member,
            availability_type=AVAILABILITY_TYPE.SPECIFIC,
            specific_date=date_obj
        )
        
        if specific_availabilities.exists():
            # Check if it's an off day
            if specific_availabilities.filter(off_day=True).exists():
                return JsonResponse({
                    'success': True,
                    'timeslots': [],
                    'message': 'Staff member is not available on this date'
                })
            # Use specific availability
            availabilities = specific_availabilities.filter(off_day=False)
        else:
            # Use weekly availability
            availabilities = StaffAvailability.objects.filter(
                staff_member=staff_member,
                availability_type=AVAILABILITY_TYPE.WEEKLY,
                weekday=weekday,
                off_day=False
            )
        
        if not availabilities.exists():
            return JsonResponse({
                'success': True,
                'timeslots': [],
                'message': 'No availability set for this day'
            })
        
        # Generate timeslots
        timeslots = []
        for availability in availabilities:
            start_time = availability.start_time
            end_time = availability.end_time
            
            # Generate 30-minute intervals
            current_time = datetime.combine(date_obj, start_time)
            end_datetime = datetime.combine(date_obj, end_time)
            
            while current_time + timedelta(minutes=duration_minutes) <= end_datetime:
                slot_start = current_time.time()
                slot_end = (current_time + timedelta(minutes=duration_minutes)).time()
                
                # Check if this slot conflicts with existing bookings
                conflicting_bookings = Booking.objects.filter(
                    business=business,
                    booking_date=date_obj,
                    start_time__lt=slot_end,
                    end_time__gt=slot_start,
                    status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.RESCHEDULED]
                ).exclude(id=booking_id)
                
                # Check if staff has conflicting bookings
                from .models import BookingStaffAssignment
                staff_conflicts = BookingStaffAssignment.objects.filter(
                    staff_member=staff_member,
                    booking__booking_date=date_obj,
                    booking__start_time__lt=slot_end,
                    booking__end_time__gt=slot_start,
                    booking__status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.RESCHEDULED]
                ).exclude(booking_id=booking_id)
                
                is_available = not conflicting_bookings.exists() and not staff_conflicts.exists()
                
                timeslots.append({
                    'start_time': slot_start.strftime('%H:%M'),
                    'end_time': slot_end.strftime('%H:%M'),
                    'display_time': slot_start.strftime('%I:%M %p'),
                    'available': is_available
                })
                
                current_time += timedelta(minutes=30)
        
        return JsonResponse({
            'success': True,
            'timeslots': timeslots,
            'duration': duration_minutes
        })
        
    except Booking.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Booking not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def reschedule_booking(request, booking_id):
    """
    Reschedule a booking to a new date and time
    """
    business = get_user_business(request.user)
    if not business:
        return JsonResponse({'success': False, 'message': 'Business not found'}, status=404)
    
    try:
        booking = Booking.objects.get(id=booking_id, business=business)
        
        # Check if booking can be rescheduled (must be at least 24 hours before appointment)
        from datetime import datetime, timedelta
        booking_datetime = timezone.make_aware(datetime.combine(booking.booking_date, booking.start_time))
        now = timezone.now()
        hours_until_booking = (booking_datetime - now).total_seconds() / 3600
        
        if hours_until_booking < 24:
            return JsonResponse({
                'success': False,
                'message': 'Cannot reschedule booking less than 24 hours before appointment time'
            }, status=400)
        
        # Get reschedule data from request
        data = json.loads(request.body)
        new_date_str = data.get('new_date')
        new_start_time_str = data.get('new_start_time')
        new_end_time_str = data.get('new_end_time')
        reason = data.get('reason', '')
        
        if not all([new_date_str, new_start_time_str, new_end_time_str]):
            return JsonResponse({
                'success': False,
                'message': 'New date and time are required'
            }, status=400)
        
        if not reason:
            return JsonResponse({
                'success': False,
                'message': 'Reschedule reason is required'
            }, status=400)
        
        # Parse new date and time
        new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
        new_start_time = datetime.strptime(new_start_time_str, '%H:%M').time()
        new_end_time = datetime.strptime(new_end_time_str, '%H:%M').time()
        
        # Store old values for event tracking
        old_date = booking.booking_date
        old_start_time = booking.start_time
        old_end_time = booking.end_time
        
        # Update booking
        booking.booking_date = new_date
        booking.start_time = new_start_time
        booking.end_time = new_end_time
        booking.status = BookingStatus.RESCHEDULED
        booking.save()
        
        # Create booking event
        from .models import BookingEvent, BookingEventType
        rescheduled_event_type = BookingEventType.objects.filter(
            business=business,
            event_key='rescheduled',
            is_enabled=True
        ).first()
        
        if rescheduled_event_type:
            BookingEvent.objects.create(
                booking=booking,
                event_type=rescheduled_event_type,
                description=f'Booking rescheduled from {old_date} {old_start_time.strftime("%I:%M %p")} to {new_date} {new_start_time.strftime("%I:%M %p")}',
                reason=reason,
                old_date=old_date,
                old_start_time=old_start_time,
                old_end_time=old_end_time,
                new_date=new_date,
                new_start_time=new_start_time,
                new_end_time=new_end_time
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Booking rescheduled successfully'
        })
        
    except Booking.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Booking not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
