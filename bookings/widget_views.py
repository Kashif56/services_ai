"""
Widget API views for public booking widget
These endpoints don't require authentication and use business_slug for identification
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from business.models import Business, ServiceOffering, BusinessCustomField, ServiceItem, ServiceOfferingItem
from .models import Booking, BookingField, BookingServiceItem, StaffMember, BookingStaffAssignment
from leads.models import Lead
from .availability import check_timeslot_availability
import json
from decimal import Decimal
from datetime import datetime


def get_widget_config(request, business_id):
    """
    Get widget configuration for a business
    Returns: business info, services, custom fields
    """
    try:
        business = Business.objects.get(id=business_id, is_active=True)
        
        # Get active service offerings
        services = ServiceOffering.objects.filter(
            business=business, 
            is_active=True
        ).order_by('name')
        
        services_data = [{
            'id': str(service.id),
            'name': service.name,
            'description': service.description,
            'price': float(service.price),
            'duration': service.duration,
        } for service in services]
        
        # Get custom fields
        custom_fields = BusinessCustomField.objects.filter(
            business=business, 
            is_active=True
        ).order_by('display_order', 'name')
        
        fields_data = [{
            'id': str(field.id),
            'slug': field.slug,
            'name': field.name,
            'field_type': field.field_type,
            'required': field.required,
            'placeholder': field.placeholder,
            'help_text': field.help_text,
            'options': field.options if field.field_type == 'select' else []
        } for field in custom_fields]
        
        return JsonResponse({
            'success': True,
            'business': {
                'id': str(business.id),
                'name': business.name,
                'logo': business.logo.url if business.logo else None,
                'primary_color': getattr(business, 'primary_color', '#8b5cf6'),
            },
            'services': services_data,
            'custom_fields': fields_data
        })
        
    except Business.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Business not found'
        }, status=404)


def get_widget_service_items(request, business_id, service_id):
    """
    Get service items for a specific service offering
    """
    try:
        business = Business.objects.get(id=business_id, is_active=True)
        service_offering = ServiceOffering.objects.get(
            id=service_id, 
            business=business, 
            is_active=True
        )
        
        # Get service items linked to this service offering
        service_items = ServiceItem.objects.filter(
            business=business,
            service_offering=service_offering,
            is_active=True
        )
        
        items = []
        for service_item in service_items:
            # Check if this item is required
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
            'success': True,
            'service_id': str(service_id),
            'service_name': service_offering.name,
            'items': items
        })
        
    except (Business.DoesNotExist, ServiceOffering.DoesNotExist):
        return JsonResponse({
            'success': False,
            'error': 'Service not found'
        }, status=404)


def check_widget_availability(request, business_id):
    """
    Check staff availability for a timeslot
    """
    try:
        business = Business.objects.get(id=business_id, is_active=True)
        
        # Get parameters
        date_str = request.GET.get('date')
        time_str = request.GET.get('time')
        duration_minutes = int(request.GET.get('duration_minutes', 60))
        service_offering_id = request.GET.get('service_offering_id')
        
        if not date_str or not time_str:
            return JsonResponse({
                'success': False,
                'error': 'Date and time are required'
            }, status=400)
        
        # Parse date and time
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        time_obj = datetime.strptime(time_str, '%H:%M').time()
        start_time = datetime.combine(date_obj, time_obj)
        
        # Get service if provided
        service = None
        if service_offering_id:
            try:
                service = ServiceOffering.objects.get(
                    id=service_offering_id, 
                    business=business
                )
            except ServiceOffering.DoesNotExist:
                pass
        
        # Check availability
        is_available, reason, available_staff = check_timeslot_availability(
            business.id,
            start_time,
            duration_minutes,
            service
        )
        
        result = {
            'success': True,
            'is_available': is_available,
            'reason': reason if not is_available else None,
            'available_staff': available_staff
        }
        
        # Get alternate timeslots if not available
        if not is_available:
            from .availability import get_alternate_timeslots
            alternate_slots = get_alternate_timeslots(
                business.id,
                date_obj,
                time_obj,
                duration_minutes,
                service_offering_id,
                None
            )
            result['alternate_slots'] = alternate_slots
        
        return JsonResponse(result)
        
    except Business.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Business not found'
        }, status=404)
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid parameters: {str(e)}'
        }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def create_widget_booking(request, business_id):
    """
    Create a booking from the widget
    This endpoint doesn't require authentication
    """
    try:
        business = Business.objects.get(id=business_id, is_active=True)
        
        # Parse JSON data
        data = json.loads(request.body)
        
        # Extract booking data
        service_type_id = data.get('service_type')
        booking_date = data.get('booking_date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        location_type = data.get('location_type', 'business')
        location_details = data.get('location_details', '')
        notes = data.get('notes', '')
        staff_member_id = data.get('staff_member_id')
        
        # Client information
        client_name = data.get('client_name')
        client_email = data.get('client_email')
        client_phone = data.get('client_phone')
        
        # Custom fields
        custom_fields_data = data.get('custom_fields', {})
        
        # Service items
        service_items_data = data.get('service_items', {})
        
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
            return JsonResponse({
                'success': False,
                'errors': errors
            }, status=400)
        
        # Get service offering
        try:
            service_offering = ServiceOffering.objects.get(
                id=service_type_id, 
                business=business
            )
        except ServiceOffering.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid service selected.'
            }, status=400)
        
        # Get staff member
        try:
            staff_member = StaffMember.objects.get(
                id=staff_member_id, 
                business=business
            )
        except StaffMember.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Selected staff member not found.'
            }, status=400)
        
        # Check if lead exists with this email
        lead = Lead.objects.filter(
            business=business, 
            email=client_email
        ).first()
        
        # Create or update lead
        if not lead:
            # Extract first and last name from full name
            name_parts = client_name.strip().split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            lead = Lead.objects.create(
                business=business,
                first_name=first_name,
                last_name=last_name,
                email=client_email,
                phone=client_phone,
                source='widget',
                status='appointment_scheduled'
            )
        else:
            # Update lead status
            lead.status = 'appointment_scheduled'
            lead.save()
        
        # Create booking
        booking = Booking.objects.create(
            business=business,
            lead=lead,
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
        BookingStaffAssignment.objects.create(
            booking=booking,
            staff_member=staff_member,
            is_primary=True
        )
        
        # Save custom fields
        custom_fields = BusinessCustomField.objects.filter(
            business=business, 
            is_active=True
        )
        
        for field in custom_fields:
            field_key = f'custom_{field.slug}'
            val = custom_fields_data.get(field_key, '')
            
            # Handle boolean fields
            if field.field_type == 'boolean':
                val = 'true' if custom_fields_data.get(field_key) else 'false'
            
            # Validate required fields
            if field.required and not val and field.field_type != 'boolean':
                booking.delete()
                return JsonResponse({
                    'success': False,
                    'error': f'{field.name} is required.'
                }, status=400)
            
            BookingField.objects.create(
                booking=booking,
                field_type='business',
                business_field=field,
                value=val
            )
        
        # Save service items
        for item_id, item_data in service_items_data.items():
            try:
                service_item = ServiceItem.objects.get(
                    id=item_id, 
                    business=business
                )
                
                quantity = int(item_data.get('quantity', 1))
                field_value = item_data.get('value', '')
                
                # For non-free items with number field type
                if service_item.price_type != 'free' and service_item.field_type == 'number':
                    if field_value:
                        try:
                            quantity = int(float(field_value))
                            field_value = str(quantity)
                        except (ValueError, TypeError):
                            pass
                
                # Calculate price
                price_at_booking = service_item.calculate_price(
                    base_price=service_offering.price,
                    quantity=quantity,
                    selected_value=field_value if service_item.field_type in ['select', 'boolean'] else None
                )
                
                # Create booking service item
                booking_service_item = BookingServiceItem.objects.create(
                    booking=booking,
                    service_item=service_item,
                    quantity=quantity,
                    price_at_booking=price_at_booking
                )
                
                # Set response value
                booking_service_item.set_response_value(field_value)
                booking_service_item.save()
                
            except (ServiceItem.DoesNotExist, ValueError):
                pass
        
        return JsonResponse({
            'success': True,
            'message': 'Booking created successfully!',
            'booking_id': str(booking.id)
        })
        
    except Business.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Business not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=500)
