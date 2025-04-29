from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import models
from business.models import ServiceOffering, BusinessCustomField, ServiceItem, ServiceOfferingItem, Industry, IndustryField
from .models import Booking, BookingField, BookingServiceItem, BookingStatus
from django.utils import timezone
import json

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

    if request.method == 'POST':
        # Basic Booking fields
        service_type_id = request.POST.get('service_type')
        booking_date = request.POST.get('booking_date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        location_type = request.POST.get('location_type')
        location_details = request.POST.get('location_details')
        notes = request.POST.get('notes')
        
        # Client information
        client_name = request.POST.get('client_name')
        client_email = request.POST.get('client_email')
        client_phone = request.POST.get('client_phone')

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

        # Create Booking
        booking = Booking.objects.create(
            business=business,
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
        for item_id in service_items:
            try:
                service_item = ServiceItem.objects.get(id=item_id, business=business)
                quantity = int(request.POST.get(f'item_quantity_{item_id}', 1))
                
                # Calculate price at booking time
                price_at_booking = service_item.calculate_price(base_price=service_offering.price, quantity=quantity)
                
                BookingServiceItem.objects.create(
                    booking=booking,
                    service_item=service_item,
                    quantity=quantity,
                    price_at_booking=price_at_booking
                )
            except (ServiceItem.DoesNotExist, ValueError):
                # Log this but don't fail the booking
                pass

        messages.success(request, 'Booking created successfully!')
        return redirect(reverse('bookings:index'))

    # GET
    return render(request, 'bookings/create_booking.html', {
        'service_offerings': service_offerings,
        'custom_fields': custom_fields,
    })

@login_required
def booking_detail(request, booking_id):
    """View for displaying detailed information about a booking"""
    business = getattr(request.user, 'business', None)
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
        
        # Calculate service items total separately
        service_items_total = 0
        for item in service_items:
           
            service_items_total += item.price_at_booking
        
        # Calculate total price
        total_price = booking.service_offering.price + service_items_total
        
        # Create a timeline of booking events
        timeline = [
            {
                'date': booking.created_at,
                'status': 'created',
                'icon': 'fa-plus-circle',
                'description': 'Booking created'
            }
        ]
        
        # Add status changes to timeline if applicable
        if booking.status != 'pending':
            timeline.append({
                'date': booking.updated_at,
                'status': booking.status,
                'icon': {
                    'confirmed': 'fa-check',
                    'cancelled': 'fa-times',
                    'completed': 'fa-check-double',
                    'rescheduled': 'fa-calendar-alt',
                    'no_show': 'fa-user-times'
                }.get(booking.status, 'fa-info-circle'),
                'description': f'Booking {booking.status}'
            })
        
        # Sort timeline by date
        timeline = sorted(timeline, key=lambda x: x['date'], reverse=True)
        
        return render(request, 'bookings/booking_detail.html', {
            'title': f'Booking: {booking.name}',
            'booking': booking,
            'business_fields': business_fields,
            'industry_fields': industry_fields,
            'service_items': service_items,
            'service_items_total': service_items_total,
            'total_price': total_price,
            'timeline': timeline
        })
        timeline_events.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return render(request, 'bookings/booking_detail.html', {
            'title': f'Booking: {booking.name}',
            'booking': booking,
            'custom_fields': custom_fields,
            'industry_fields': industry_fields,
            'service_items': service_items,
            'total_price': total_price,
            'timeline_events': timeline_events
        })
    except Booking.DoesNotExist:
        messages.error(request, 'Booking not found.')
        return redirect('bookings:index')

@login_required
def get_service_items(request, service_id):
    """API endpoint to get all service items for a business"""
    business = getattr(request.user, 'business', None)
    if not business:
        return JsonResponse({'error': 'Business not found'}, status=404)
    
    try:
        # Get the service offering for reference
        service_offering = ServiceOffering.objects.get(id=service_id, business=business)
        
        # Get all service items for this business
        service_items = ServiceItem.objects.filter(business=business, is_active=True)
        
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
def get_industry_fields(request, service_id):
    """API endpoint to get industry-specific fields for a service"""
    business = getattr(request.user, 'business', None)
    if not business:
        return JsonResponse({'error': 'Business not found'}, status=404)
    
    industry = business.industry
    industry_fields = IndustryField.objects.filter(industry=industry, is_active=True)
    
    fields = []
    for field in industry_fields:
        fields.append({
            'id': field.id,
            'name': field.name,
            'slug': field.slug,
            'field_type': field.field_type,
            'options': field.options,
            'placeholder': field.placeholder,
            'help_text': field.help_text,
            'required': field.required,
            'default_value': field.default_value
        })
    
    return JsonResponse({
        'service_id': str(service_id),
        'industry_name': industry.name,
        'fields': fields
    })
