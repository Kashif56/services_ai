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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime

from .models import Business, Industry, IndustryField, BusinessConfiguration, ServiceOffering, ServiceItem, CRM_CHOICES, SMTPConfig, StripeCredentials, SquareCredentials


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
    
    # Check if user's email is verified
    from accounts.models import EmailVerification
    user_email = request.user.email
    try:
        verification = EmailVerification.objects.filter(user=request.user, email=user_email).first()
        if not verification or not verification.is_verified:
            return JsonResponse({
                'success': False,
                'message': 'Please verify your email address before registering a business.',
                'redirect_url': '/accounts/verify-email/'
            })
    except Exception as e:
        # Continue if there's an error checking verification
        # This ensures backward compatibility with existing users
        pass
    
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
            
            # Mark the email as verified in our verification system if it matches
            if data['email'] == user_email:
                try:
                    verification = EmailVerification.objects.filter(user=request.user, email=user_email).first()
                    if verification:
                        verification.is_verified = True
                        verification.save()
                except Exception:
                    pass
            
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
    print(business.id)
    
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
        # Check if service is free - check the value, not just presence
        is_free = request.POST.get('is_free', '') == 'on'
        
        # If service is free, set price to 0
        price = Decimal('0.00') if is_free else Decimal(request.POST.get('price', '0.00'))
        
        # Create new service
        service = ServiceOffering.objects.create(
            business=business,
            name=request.POST.get('name'),
            description=request.POST.get('description', ''),
            is_free=is_free,
            price=price,
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
        
        # Check if service is free - check the value, not just presence
        is_free = request.POST.get('is_free', '') == 'on'
        
        # If service is free, set price to 0
        price = Decimal('0.00') if is_free else Decimal(request.POST.get('price', '0.00'))
        
        # Update service fields
        service.name = request.POST.get('name')
        service.description = request.POST.get('description', '')
        service.is_free = is_free
        service.price = price
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
def manage_service_item(request, item_id=None):
    """
    Render the manage service item page for both add and edit
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
    # Get all services for the business
    services = ServiceOffering.objects.filter(business=business, is_active=True)
    
    context = {
        'services': services,
        'item_id': item_id,
    }
    
    return render(request, 'business/manage_service_item.html', context)


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
        service_offering_id = request.POST.get('service_offering_id')
        price_type = request.POST.get('price_type')
        price_value = request.POST.get('price_value', '0')
        duration_minutes = request.POST.get('duration_minutes', 0)
        max_quantity = request.POST.get('max_quantity', 1)
        is_optional = 'is_optional' in request.POST
        is_active = 'is_active' in request.POST
        
        # Get field type
        field_type = request.POST.get('field_type', 'text')
        
        # For free items, set price_value to 0 and allow custom field type
        if price_type == 'free':
            price_value = '0'
        else:
            # For paid items with number field type, field type must be number
            if field_type == 'number':
                field_type = 'number'
        
        # Process field options and option pricing
        field_options = None
        option_pricing = None
        
        if field_type == 'boolean':
            # Process Yes/No option pricing
            yes_price_type = request.POST.get('yes_price_type', 'free')
            yes_price_value = float(request.POST.get('yes_price_value', 0) or 0)
            no_price_type = request.POST.get('no_price_type', 'free')
            no_price_value = float(request.POST.get('no_price_value', 0) or 0)
            
            option_pricing = {
                'yes': {
                    'price_type': yes_price_type,
                    'price_value': yes_price_value
                },
                'no': {
                    'price_type': no_price_type,
                    'price_value': no_price_value
                }
            }
            
            # If any option is paid, set overall price_type to paid
            if yes_price_type == 'paid' or no_price_type == 'paid':
                price_type = 'paid'
                # Set price_value to the max of the two options
                price_value = str(max(yes_price_value, no_price_value))
            else:
                price_type = 'free'
                price_value = '0'
                
        elif field_type == 'select':
            # Process select options with pricing
            option_pricing = {}
            option_names = request.POST.getlist('option_name[]')
            option_price_types = request.POST.getlist('option_price_type[]')
            option_price_values = request.POST.getlist('option_price_value[]')
            
            # Build field_options list and option_pricing dict
            field_options = []
            has_paid_option = False
            max_price = 0
            
            for i, option_name in enumerate(option_names):
                if option_name.strip():
                    field_options.append(option_name.strip())
                    opt_price_type = option_price_types[i] if i < len(option_price_types) else 'free'
                    opt_price_value = float(option_price_values[i] or 0) if i < len(option_price_values) else 0
                    
                    option_pricing[option_name.strip().lower()] = {
                        'price_type': opt_price_type,
                        'price_value': opt_price_value
                    }
                    
                    # Track if any option is paid
                    if opt_price_type == 'paid':
                        has_paid_option = True
                        max_price = max(max_price, opt_price_value)
            
            # If any option is paid, set overall price_type to paid
            if has_paid_option:
                price_type = 'paid'
                price_value = str(max_price)
            else:
                price_type = 'free'
                price_value = '0'
        
        # Validate required fields
        if not name or not price_type:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('business:pricing')
        
        # Get service offering if provided
        service_offering = None
        if service_offering_id:
            try:
                service_offering = ServiceOffering.objects.get(id=service_offering_id, business=business)
            except ServiceOffering.DoesNotExist:
                messages.error(request, 'Invalid service offering selected.')
                return redirect('business:pricing')
        
        # Create service item
        ServiceItem.objects.create(
            business=business,
            service_offering=service_offering,
            name=name,
            description=description,
            field_type=field_type,
            field_options=field_options,
            price_type=price_type,
            price_value=Decimal(price_value),
            option_pricing=option_pricing,
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
        service_offering_id = request.POST.get('service_offering_id')
        price_type = request.POST.get('price_type')
        price_value = request.POST.get('price_value', '0')
        duration_minutes = request.POST.get('duration_minutes', 0)
        max_quantity = request.POST.get('max_quantity', 1)
        is_optional = 'is_optional' in request.POST
        is_active = 'is_active' in request.POST
        
        # Get field type
        field_type = request.POST.get('field_type', 'text')
        
        # For free items, set price_value to 0 and allow custom field type
        if price_type == 'free':
            price_value = '0'
        else:
            # For paid items with number field type, field type must be number
            if field_type == 'number':
                field_type = 'number'
        
        # Process field options and option pricing
        field_options = None
        option_pricing = None
        
        if field_type == 'boolean':
            # Process Yes/No option pricing
            yes_price_type = request.POST.get('yes_price_type', 'free')
            yes_price_value = float(request.POST.get('yes_price_value', 0) or 0)
            no_price_type = request.POST.get('no_price_type', 'free')
            no_price_value = float(request.POST.get('no_price_value', 0) or 0)
            
            option_pricing = {
                'yes': {
                    'price_type': yes_price_type,
                    'price_value': yes_price_value
                },
                'no': {
                    'price_type': no_price_type,
                    'price_value': no_price_value
                }
            }
            
            # If any option is paid, set overall price_type to paid
            if yes_price_type == 'paid' or no_price_type == 'paid':
                price_type = 'paid'
                # Set price_value to the max of the two options
                price_value = str(max(yes_price_value, no_price_value))
            else:
                price_type = 'free'
                price_value = '0'
                
        elif field_type == 'select':
            # Process select options with pricing
            option_pricing = {}
            option_names = request.POST.getlist('option_name[]')
            option_price_types = request.POST.getlist('option_price_type[]')
            option_price_values = request.POST.getlist('option_price_value[]')
            
            # Build field_options list and option_pricing dict
            field_options = []
            has_paid_option = False
            max_price = 0
            
            for i, option_name in enumerate(option_names):
                if option_name.strip():
                    field_options.append(option_name.strip())
                    opt_price_type = option_price_types[i] if i < len(option_price_types) else 'free'
                    opt_price_value = float(option_price_values[i] or 0) if i < len(option_price_values) else 0
                    
                    option_pricing[option_name.strip().lower()] = {
                        'price_type': opt_price_type,
                        'price_value': opt_price_value
                    }
                    
                    # Track if any option is paid
                    if opt_price_type == 'paid':
                        has_paid_option = True
                        max_price = max(max_price, opt_price_value)
            
            # If any option is paid, set overall price_type to paid
            if has_paid_option:
                price_type = 'paid'
                price_value = str(max_price)
            else:
                price_type = 'free'
                price_value = '0'
        
        # Validate required fields
        if not item_id or not name or not price_type:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('business:pricing')
        
        # Get service item and verify ownership
        service_item = get_object_or_404(ServiceItem, pk=item_id)
        if service_item.business != business:
            messages.error(request, 'You do not have permission to edit this service item.')
            return redirect('business:pricing')
        
        # Get service offering if provided
        service_offering = None
        if service_offering_id:
            try:
                service_offering = ServiceOffering.objects.get(id=service_offering_id, business=business)
            except ServiceOffering.DoesNotExist:
                messages.error(request, 'Invalid service offering selected.')
                return redirect('business:pricing')
        
        # Update service item
        service_item.name = name
        service_item.description = description
        service_item.service_offering = service_offering
        service_item.field_type = field_type
        service_item.field_options = field_options
        service_item.price_type = price_type
        service_item.price_value = Decimal(price_value)
        service_item.option_pricing = option_pricing
        service_item.duration_minutes = int(duration_minutes)
        service_item.max_quantity = int(max_quantity)
        service_item.is_optional = False if is_optional else True
        service_item.is_active = True if is_active else False
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
            'service_offering_id': str(service_item.service_offering.id) if service_item.service_offering else '',
            'field_type': service_item.field_type,
            'field_options': service_item.field_options,
            'price_type': service_item.price_type,
            'price_value': float(service_item.price_value),
            'option_pricing': service_item.option_pricing,
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
        return JsonResponse({'error': 'No business found'}, status=403)
    
    business = request.user.business
    
    try:
        # Get service and verify it belongs to this business
        service = get_object_or_404(ServiceOffering, id=service_id, business=business)
        
        # Return service data as JSON
        return JsonResponse({
            'id': service.id,
            'name': service.name,
            'description': service.description or '',
            'is_free': service.is_free,
            'price': str(service.price),
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

# Payment Gateway Management Views
@login_required
def payment_gateways(request):
    """
    Render the payment gateways management page
    Shows Stripe and Square integration options
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
    context = {
        'business': business,
    }
    
    return render(request, 'business/payment_gateways.html', context)


@login_required
def save_stripe_credentials(request):
    """
    Save Stripe credentials for the business
    Creates or updates the StripeCredentials model
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    business = request.user.business
    stripe_secret_key = request.POST.get('stripe_secret_key')
    stripe_publishable_key = request.POST.get('stripe_publishable_key')
    
    if not stripe_secret_key or not stripe_publishable_key:
        return JsonResponse({'success': False, 'message': 'All fields are required'})
    
    try:
        # Try to get existing credentials or create new ones
        stripe_credentials, created = StripeCredentials.objects.get_or_create(
            business=business,
            defaults={
                'stripe_secret_key': stripe_secret_key,
                'stripe_publishable_key': stripe_publishable_key
            }
        )
        
        # If credentials already existed, update them
        if not created:
            stripe_credentials.stripe_secret_key = stripe_secret_key
            stripe_credentials.stripe_publishable_key = stripe_publishable_key
            stripe_credentials.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Stripe credentials saved successfully!'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })


@login_required
def save_square_credentials(request):
    """
    Save Square credentials for the business
    Creates or updates the SquareCredentials model
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    business = request.user.business
    access_token = request.POST.get('access_token')
    app_id = request.POST.get('app_id')
    location_id = request.POST.get('location_id')
    
    if not access_token or not app_id or not location_id:
        return JsonResponse({'success': False, 'message': 'All fields are required'})
    
    try:
        # Try to get existing credentials or create new ones
        square_credentials, created = SquareCredentials.objects.get_or_create(
            business=business,
            defaults={
                'access_token': access_token,
                'app_id': app_id,
                'location_id': location_id
            }
        )
        
        # If credentials already existed, update them
        if not created:
            square_credentials.access_token = access_token
            square_credentials.app_id = app_id
            square_credentials.location_id = location_id
            square_credentials.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Square credentials saved successfully!'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })


@login_required
@require_http_methods(["POST"])
def set_default_payment_gateway(request):
    """
    Set the default payment gateway for the business
    Updates the default_payment_method field in the Business model
    """
    try:
        data = json.loads(request.body)
        gateway = data.get('gateway')
        
        if not gateway or gateway not in ['stripe', 'square']:
            return JsonResponse({
                'success': False,
                'message': 'Invalid payment gateway specified'
            })
        
        business = request.user.business
        
        # Check if the specified gateway is configured
        if gateway == 'stripe' and not hasattr(business, 'stripe_credentials'):
            return JsonResponse({
                'success': False,
                'message': 'Stripe credentials not configured'
            })
        elif gateway == 'square' and not hasattr(business, 'square_credentials'):
            return JsonResponse({
                'success': False,
                'message': 'Square credentials not configured'
            })
        
        # Update the default payment method
        business.default_payment_method = gateway
        business.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{gateway.capitalize()} has been set as your default payment gateway'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })


@login_required
def test_smtp_connection(request):
    """
    Test SMTP connection with provided credentials
    Sends a test email to the business email
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')




@login_required
def smtp_config(request):
    """
    Render the SMTP configuration page
    Shows SMTP settings for email sending
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
    # Get or initialize SMTP config
    smtp_config = None
    try:
        smtp_config = SMTPConfig.objects.get(business=business)
    except SMTPConfig.DoesNotExist:
        pass
    
    context = {
        'business': business,
        'smtp_config': smtp_config,
    }
    
    return render(request, 'business/smtp_config.html', context)


@login_required
@require_http_methods(["POST"])
def update_smtp_config(request):
    """
    Update SMTP configuration settings
    Handles form submission from the SMTP configuration page
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
    try:
        # Get form data
        host = request.POST.get('host')
        port = request.POST.get('port')
        username = request.POST.get('username')
        password = request.POST.get('password')
        reply_to = request.POST.get('reply_to')
        from_email = request.POST.get('from_email')
        
        # Validate required fields
        if not host or not port or not username or not password or not reply_to or not from_email:
            messages.error(request, 'All fields are required.')
            return redirect('business:smtp_config')
        
        # Convert port to integer
        try:
            port = int(port)
        except ValueError:
            messages.error(request, 'Port must be a number.')
            return redirect('business:smtp_config')
        
        # Update or create SMTP config
        smtp_config, created = SMTPConfig.objects.update_or_create(
            business=business,
            defaults={
                'host': host,
                'port': port,
                'username': username,
                'password': password,
                'reply_to': reply_to,
                'from_email': from_email,
            }
        )
        
        messages.success(request, 'SMTP configuration updated successfully!')
    except Exception as e:
        messages.error(request, f'Error updating SMTP configuration: {str(e)}')
    
    return redirect('business:smtp_config')


@login_required
@require_http_methods(["POST"])
def test_smtp_config(request):
    """
    Test SMTP configuration by sending a test email
    Returns JSON response with success/error message
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        return JsonResponse({
            'success': False,
            'message': 'Please register your business first.'
        })
    
    business = request.user.business
    
    try:
        # Check if this is an API request with JSON data
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                # Use provided SMTP settings or get from database
                host = data.get('host')
                port = data.get('port')
                username = data.get('username')
                password = data.get('password')
                from_email = data.get('from_email')
                reply_to = data.get('reply_to')
                test_email = data.get('test_email', business.email)
                
                # If any field is missing, try to get from database
                if not all([host, port, username, password, from_email, reply_to]):
                    try:
                        smtp_config = SMTPConfig.objects.get(business=business)
                        host = host or smtp_config.host
                        port = port or smtp_config.port
                        username = username or smtp_config.username
                        password = password or smtp_config.password
                        from_email = from_email or smtp_config.from_email
                        reply_to = reply_to or smtp_config.reply_to
                    except SMTPConfig.DoesNotExist:
                        return JsonResponse({
                            'success': False,
                            'message': 'SMTP configuration not found and incomplete data provided.'
                        })
            except json.JSONDecodeError:
                # Not a JSON request, continue with form data
                data = None
        else:
            # Get data from form submission
            data = None
            host = request.POST.get('host')
            port = request.POST.get('port')
            username = request.POST.get('username')
            password = request.POST.get('password')
            from_email = request.POST.get('from_email')
            reply_to = request.POST.get('reply_to')
            test_email = business.email
        
        # If no data provided, try to get from database
        if not all([host, port, username, password, from_email, reply_to]):
            try:
                smtp_config = SMTPConfig.objects.get(business=business)
                host = host or smtp_config.host
                port = port or smtp_config.port
                username = username or smtp_config.username
                password = password or smtp_config.password
                from_email = from_email or smtp_config.from_email
                reply_to = reply_to or smtp_config.reply_to
            except SMTPConfig.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'SMTP configuration not found and incomplete data provided.'
                })
        
        # Convert port to integer if it's a string
        if isinstance(port, str):
            port = int(port)
        
        # Create test email
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = test_email
        msg['Subject'] = 'Test Email from Services AI'
        msg['Reply-To'] = reply_to
        
        # Email body
        body = f"""
        <html>
        <body>
            <h2>Test Email from Services AI</h2>
            <p>This is a test email from your Services AI SMTP configuration.</p>
            <p>If you received this email, your SMTP configuration is working correctly.</p>
            <p><strong>Business:</strong> {business.name}</p>
            <p><strong>SMTP Host:</strong> {host}</p>
            <p><strong>From Email:</strong> {from_email}</p>
            <p><strong>Reply-To:</strong> {reply_to}</p>
            <p><strong>Time Sent:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Connect to SMTP server and send email
        server = smtplib.SMTP(host, port)
        server.starttls()  # Start TLS encryption
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        
        return JsonResponse({
            'success': True,
            'message': f'Test email sent successfully to {test_email}!'
        })
    except smtplib.SMTPAuthenticationError:
        return JsonResponse({
            'success': False,
            'message': 'SMTP authentication failed. Please check your username and password.'
        })
    except smtplib.SMTPConnectError:
        return JsonResponse({
            'success': False,
            'message': 'Failed to connect to the SMTP server. Please check your host and port.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })


@login_required
def booking_preferences(request):
    """
    Manage booking event types and reminder types preferences
    """
    business = getattr(request.user, 'business', None)
    if not business:
        messages.error(request, 'Business not found.')
        return redirect('business:dashboard')
    
    from bookings.models import BookingEventType, ReminderType
    
    # Initialize default types if they don't exist
    if not BookingEventType.objects.filter(business=business).exists():
        BookingEventType.create_default_types(business)
    
    if not ReminderType.objects.filter(business=business).exists():
        ReminderType.create_default_types(business)
    
    # Get all event types and reminder types
    event_types = BookingEventType.objects.filter(business=business).order_by('display_order')
    reminder_types = ReminderType.objects.filter(business=business).order_by('display_order')
    
    return render(request, 'business/booking_preferences.html', {
        'title': 'Booking Preferences',
        'event_types': event_types,
        'reminder_types': reminder_types,
    })


@login_required
@require_http_methods(["POST"])
def update_event_type(request, event_type_id):
    """
    Update a booking event type configuration
    """
    business = getattr(request.user, 'business', None)
    if not business:
        return JsonResponse({'success': False, 'message': 'Business not found'}, status=404)
    
    from bookings.models import BookingEventType
    
    try:
        event_type = BookingEventType.objects.get(id=event_type_id, business=business)
        data = json.loads(request.body)
        
        # Update fields
        if 'name' in data:
            event_type.name = data['name']
        if 'icon' in data:
            event_type.icon = data['icon']
        if 'color' in data:
            event_type.color = data['color']
        if 'is_enabled' in data:
            event_type.is_enabled = data['is_enabled']
        if 'show_in_timeline' in data:
            event_type.show_in_timeline = data['show_in_timeline']
        if 'requires_reason' in data:
            event_type.requires_reason = data['requires_reason']
        if 'display_order' in data:
            event_type.display_order = data['display_order']
        
        event_type.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Event type updated successfully'
        })
    except BookingEventType.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Event type not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def update_reminder_type(request, reminder_type_id):
    """
    Update a reminder type configuration
    """
    business = getattr(request.user, 'business', None)
    if not business:
        return JsonResponse({'success': False, 'message': 'Business not found'}, status=404)
    
    from bookings.models import ReminderType
    
    try:
        reminder_type = ReminderType.objects.get(id=reminder_type_id, business=business)
        data = json.loads(request.body)
        
        # Update fields
        if 'name' in data:
            reminder_type.name = data['name']
        if 'icon' in data:
            reminder_type.icon = data['icon']
        if 'is_enabled' in data:
            reminder_type.is_enabled = data['is_enabled']
        if 'default_hours_before' in data:
            reminder_type.default_hours_before = data['default_hours_before']
        if 'display_order' in data:
            reminder_type.display_order = data['display_order']
        
        reminder_type.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Reminder type updated successfully'
        })
    except ReminderType.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Reminder type not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
