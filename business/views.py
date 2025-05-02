from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.urls import reverse
import json
from decimal import Decimal

from .models import Business, Industry, IndustryField, BusinessConfiguration, ServiceOffering, ServiceItem, CRM_CHOICES


@login_required
@ensure_csrf_cookie
def business_registration(request):
    """Render the business registration page"""
    # Check if user already has a business
    if hasattr(request.user, 'business'):
        messages.info(request, 'You already have a registered business.')
        return redirect('business:dashboard')
        
    return render(request, 'business/register.html')


@login_required
@require_http_methods(["GET"])
def get_industries(request):
    """API endpoint to get all active industries"""
    industries = Industry.objects.filter(is_active=True).values('id', 'name', 'description', 'icon')
    return JsonResponse({'industries': list(industries)})



@login_required
@require_http_methods(["POST"])
def register_business(request):
    """API endpoint to register a business"""
    # Check if user already has a business
    if hasattr(request.user, 'business'):
        return JsonResponse({
            'success': False,
            'message': 'You already have a registered business.'
        })
    
    try:
        # Parse JSON data from request body
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['business_name', 'industry', 'phone_number', 'email']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'{field.replace("_", " ").title()} is required.'
                })
        
        # Get industry
        try:
            industry = Industry.objects.get(pk=data['industry'], is_active=True)
        except Industry.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Selected industry does not exist.'
            })
        
        # Create business with transaction to ensure atomicity
        with transaction.atomic():
            # Create business
            business = Business.objects.create(
                name=data['business_name'],
                user=request.user,
                industry=industry,
                phone_number=data['phone_number'],
                email=data['email'],
                website=data.get('website', ''),
                address=data.get('address', ''),
                city=data.get('city', ''),
                state=data.get('state', ''),
                zip_code=data.get('zip_code', ''),
                description=data.get('business_description', '')
            )
            
               # Create business configuration
            BusinessConfiguration.objects.create(business=business)
            
            return JsonResponse({
                'success': True,
                'message': 'Business registered successfully!',
                'redirect_url': '/dashboard/'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })


@login_required
def business_profile(request):
    """
    Render the business profile page
    Requires user to be logged in and have a business
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    # Get business data
    business = request.user.business
    
    context = {
        'business': business,
    }
    
    return render(request, 'business/profile.html', context)


@login_required
@require_http_methods(["POST"])
def update_profile(request):
    """
    Update business profile information
    Handles form submission from the profile page
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
    # Process form data
    try:
        # Update business fields
        business.name = request.POST.get('name', business.name)
        business.email = request.POST.get('email', business.email)
        business.phone_number = request.POST.get('phone_number', business.phone_number)
        business.website = request.POST.get('website', business.website)
        business.address = request.POST.get('address', business.address)
        business.city = request.POST.get('city', business.city)
        business.state = request.POST.get('state', business.state)
        business.zip_code = request.POST.get('zip_code', business.zip_code)
        business.description = request.POST.get('description', business.description)
        
        # Handle logo upload if provided
        if 'logo' in request.FILES:
            business.logo = request.FILES['logo']
        
        # Save changes
        business.save()
        
        messages.success(request, 'Business profile updated successfully!')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
    
    return redirect('business:profile')




@login_required
@require_http_methods(["GET"])
def business_pricing(request):
    """
    Render the service pricing configuration page
    Shows all services and packages for the business
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
    # Get all services for this business
    services = ServiceOffering.objects.filter(business=business).order_by('name')
    
    # Get all service items for this business
    service_items = ServiceItem.objects.filter(business=business).order_by('name')
    
    context = {
        'business': business,
        'services': services,
        'service_items': service_items
    }
    
    return render(request, 'business/pricing.html', context)


@login_required
@require_http_methods(["GET"])
def booking_settings(request):
    """
    Render the booking settings configuration page
    Placeholder for future implementation
    """
    return render(request, 'business/booking_settings.html')


@login_required
@require_http_methods(["GET"])
def notification_preferences(request):
    """
    Render the notification preferences configuration page
    Placeholder for future implementation
    """
    return render(request, 'business/notifications.html')


@login_required
@require_http_methods(["GET"])
def upgrade_plan(request):
    """
    Render the plan upgrade page
    Placeholder for future implementation
    """
    return render(request, 'business/upgrade.html')


@login_required
@require_http_methods(["POST"])
def add_service(request):
    """
    Add a new service to the business
    Handles form submission from the pricing page
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
    try:
        # Create new service
        service = ServiceOffering.objects.create(
            business=business,
            name=request.POST.get('name'),
            description=request.POST.get('description', ''),
            price=request.POST.get('price'),
            duration=request.POST.get('duration'),
            icon=request.POST.get('icon', 'concierge-bell'),
            color=request.POST.get('color', '#6366f1'),
            is_active='is_active' in request.POST
        )
        
        messages.success(request, f'Service "{service.name}" added successfully!')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
    
    return redirect('business:pricing')


@login_required
@require_http_methods(["POST"])
def update_service(request):
    """
    Update an existing service
    Handles form submission from the pricing page
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    service_id = request.POST.get('service_id')
    
    if not service_id:
        messages.error(request, 'Service ID is required')
        return redirect('business:pricing')
    
    try:
        # Get service and verify it belongs to this business
        service = get_object_or_404(ServiceOffering, id=service_id, business=business)
        
        # Update service fields
        service.name = request.POST.get('name')
        service.description = request.POST.get('description', '')
        service.price = request.POST.get('price')
        service.duration = request.POST.get('duration')
        service.icon = request.POST.get('icon', 'concierge-bell')
        service.color = request.POST.get('color', '#6366f1')
        service.is_active = 'is_active' in request.POST
        
        # Save changes
        service.save()
        
        messages.success(request, f'Service "{service.name}" updated successfully!')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
    
    return redirect('business:pricing')


@login_required
@require_http_methods(["POST"])
def delete_service(request):
    """
    Delete an existing service
    Handles form submission from the pricing page
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    service_id = request.POST.get('service_id')
    
    if not service_id:
        messages.error(request, 'Service ID is required')
        return redirect('business:pricing')
    
    try:
        # Get service and verify it belongs to this business
        service = get_object_or_404(ServiceOffering, id=service_id, business=business)
        service_name = service.name
        
        # Use a transaction to ensure atomicity
        with transaction.atomic():
            # First, handle any related objects that might cause constraint issues
            # Check for any StaffServiceAssignments related to this service
            from bookings.models import StaffServiceAssignment, Booking
            
            # Delete any staff service assignments for this offering
            StaffServiceAssignment.objects.filter(service_offering_id=service_id).delete()
            
            # Update any bookings that reference this service offering
            Booking.objects.filter(service_offering_id=service_id).update(service_offering=None)
            
            # Now delete the service offering
            service.delete()
        
        messages.success(request, f'Service "{service_name}" deleted successfully!')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
    
    return redirect('business:pricing')


# Service Item Management

@login_required
@require_http_methods(["POST"])
def add_service_item(request):
    """
    Add a new service item to the business
    Handles form submission from the pricing page
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
    try:
        # Get form data
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        price_type = request.POST.get('price_type')
        price_value = request.POST.get('price_value')
        duration_minutes = request.POST.get('duration_minutes', 0)
        max_quantity = request.POST.get('max_quantity', 1)
        is_optional = 'is_optional' in request.POST
        is_active = 'is_active' in request.POST
        
        # Validate required fields
        if not name or not price_type or not price_value:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('business:pricing')
        
        # Create service item
        ServiceItem.objects.create(
            business=business,
            name=name,
            description=description,
            price_type=price_type,
            price_value=Decimal(price_value),
            duration_minutes=int(duration_minutes),
            max_quantity=int(max_quantity),
            is_optional=is_optional,
            is_active=is_active
        )
        
        messages.success(request, f'Service item "{name}" added successfully!')
    except Exception as e:
        messages.error(request, f'Error adding service item: {str(e)}')
    
    return redirect('business:pricing')


@login_required
@require_http_methods(["POST"])
def edit_service_item(request):
    """
    Update an existing service item
    Handles form submission from the pricing page
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
    try:
        # Get form data
        item_id = request.POST.get('item_id')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        price_type = request.POST.get('price_type')
        price_value = request.POST.get('price_value')
        duration_minutes = request.POST.get('duration_minutes', 0)
        max_quantity = request.POST.get('max_quantity', 1)
        is_optional = 'is_optional' in request.POST
        is_active = 'is_active' in request.POST
        
        # Validate required fields
        if not item_id or not name or not price_type or not price_value:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('business:pricing')
        
        # Get service item and verify ownership
        service_item = get_object_or_404(ServiceItem, pk=item_id)
        if service_item.business != business:
            messages.error(request, 'You do not have permission to edit this service item.')
            return redirect('business:pricing')
        
        # Update service item
        service_item.name = name
        service_item.description = description
        service_item.price_type = price_type
        service_item.price_value = Decimal(price_value)
        service_item.duration_minutes = int(duration_minutes)
        service_item.max_quantity = int(max_quantity)
        service_item.is_optional = is_optional
        service_item.is_active = is_active
        service_item.save()
        
        messages.success(request, f'Service item "{name}" updated successfully!')
    except Exception as e:
        messages.error(request, f'Error updating service item: {str(e)}')
    
    return redirect('business:pricing')


@login_required
@require_http_methods(["POST"])
def delete_service_item(request):
    """
    Delete an existing service item
    Handles form submission from the pricing page
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
    try:
        # Get form data
        item_id = request.POST.get('item_id')
        
        # Validate required fields
        if not item_id:
            messages.error(request, 'Invalid request.')
            return redirect('business:pricing')
        
        # Get service item and verify ownership
        service_item = get_object_or_404(ServiceItem, pk=item_id)
        if service_item.business != business:
            messages.error(request, 'You do not have permission to delete this service item.')
            return redirect('business:pricing')
        
        # Store name for success message
        item_name = service_item.name
        
        # Delete service item
        service_item.delete()
        
        messages.success(request, f'Service item "{item_name}" deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting service item: {str(e)}')
    
    return redirect('business:pricing')


@login_required
@require_http_methods(["GET"])
def get_service_item_details(request, item_id):
    """
    API endpoint to get service item details for editing
    Returns JSON response with service item data
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        return JsonResponse({'error': 'Please register your business first.'}, status=403)
    
    business = request.user.business
    
    try:
        # Get service item and verify ownership
        service_item = get_object_or_404(ServiceItem, pk=item_id)
        if service_item.business != business:
            return JsonResponse({'error': 'You do not have permission to view this service item.'}, status=403)
        
        # Return service item data
        return JsonResponse({
            'id': str(service_item.id),
            'name': service_item.name,
            'description': service_item.description,
            'price_type': service_item.price_type,
            'price_value': float(service_item.price_value),
            'duration_minutes': service_item.duration_minutes,
            'max_quantity': service_item.max_quantity,
            'is_optional': service_item.is_optional,
            'is_active': service_item.is_active
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Package functionality has been removed as packages are not offered at the moment


# Import custom fields views
from .views_custom_fields import (
    custom_fields,
    add_custom_field,
    update_custom_field,
    delete_custom_field,
    get_custom_field_details,
    reset_custom_fields,
    reorder_custom_fields
)


@login_required
def get_service_details(request, service_id):
    """
    API endpoint to get service details for editing
    Returns JSON response with service data
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        return JsonResponse({'error': 'Please register your business first'}, status=403)
    
    business = request.user.business
    
    try:
        # Get service and verify it belongs to this business
        service = get_object_or_404(ServiceOffering, id=service_id, business=business)
        
        # Return service data as JSON
        return JsonResponse({
            'id': str(service.id),
            'name': service.name,
            'description': service.description or '',
            'price': float(service.price),
            'duration': service.duration,
            'icon': service.icon,
            'color': service.color,
            'is_active': service.is_active
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def business_configuration(request):
    """
    Render the business configuration page
    Shows voice settings, Twilio credentials, and webhook configuration
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
    # Get or create business configuration
    try:
        config, created = BusinessConfiguration.objects.get_or_create(business=business)
    except Exception as e:
        messages.error(request, f'Error retrieving configuration: {str(e)}')
        config = None
    
    # Generate webhook URL
    webhook_url = business.get_lead_webhook_url()
    
    context = {
        'business': business,
        'config': config,
        'webhook_url': webhook_url,
        'crm_choices': CRM_CHOICES
    }
    
    return render(request, 'business/configuration.html', context)


@login_required
@require_http_methods(["POST"])
def update_business_configuration(request):
    """
    Update business configuration settings
    Handles form submission from the configuration page
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
    try:
        # Get or create configuration
        config, created = BusinessConfiguration.objects.get_or_create(business=business)
        
        # Update voice settings
        config.voice_enabled = 'voice_enabled' in request.POST
        config.initial_response_delay = int(request.POST.get('initial_response_delay', 5))
        
        # Update Twilio settings
        config.twilio_phone_number = request.POST.get('twilio_phone_number', '')
        config.twilio_sid = request.POST.get('twilio_sid', '')
        config.twilio_auth_token = request.POST.get('twilio_auth_token', '')
        
        # Save changes
        config.save()
        
        messages.success(request, 'Business configuration updated successfully!')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
    
    return redirect('business:configuration')
