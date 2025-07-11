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
        # Check if service is free
        is_free = 'is_free' in request.POST
        
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
        
        # Check if service is free
        is_free = 'is_free' in request.POST
        
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
        price_value = request.POST.get('price_value', '0')
        duration_minutes = request.POST.get('duration_minutes', 0)
        max_quantity = request.POST.get('max_quantity', 1)
        is_optional = 'is_optional' in request.POST
        is_active = 'is_active' in request.POST
        
        # For free items, set price_value to 0 and allow custom field type
        if price_type == 'free':
            price_value = '0'
            field_type = request.POST.get('field_type', 'text')
        else:
            # For non-free items, field type must be number
            field_type = 'number'
        
        # Process field options for select type
        field_options = None
        if field_type == 'select' and request.POST.get('field_options'):
            # Convert comma-separated string to list
            field_options = [option.strip() for option in request.POST.get('field_options').split(',')]
        
        # Validate required fields
        if not name or not price_type or (price_type != 'free' and not price_value):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('business:pricing')
        
        # Create service item
        ServiceItem.objects.create(
            business=business,
            name=name,
            description=description,
            field_type=field_type,
            field_options=field_options,
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
        price_value = request.POST.get('price_value', '0')
        duration_minutes = request.POST.get('duration_minutes', 0)
        max_quantity = request.POST.get('max_quantity', 1)
        is_optional = 'is_optional' in request.POST
        is_active = 'is_active' in request.POST
        
        # For free items, set price_value to 0 and allow custom field type
        if price_type == 'free':
            price_value = '0'
            field_type = request.POST.get('field_type', 'text')
        else:
            # For non-free items, field type must be number
            field_type = 'number'
        
        # Process field options for select type
        field_options = None
        if field_type == 'select' and request.POST.get('field_options'):
            # Convert comma-separated string to list
            field_options = [option.strip() for option in request.POST.get('field_options').split(',')]
        
        # Validate required fields
        if not item_id or not name or not price_type or (price_type != 'free' and not price_value):
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
        service_item.field_type = field_type
        service_item.field_options = field_options
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

# Staff Management Views
@login_required
def staff_management(request):
    """
    Render the staff management page
    Shows all staff members for the business
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
    # Get all staff members for this business
    from bookings.models import StaffMember, StaffRole
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
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
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
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
    from bookings.models import StaffMember, StaffRole, StaffAvailability, WEEKDAY_CHOICES, AVAILABILITY_TYPE
    
    # Get staff member, ensuring it belongs to this business
    staff = get_object_or_404(StaffMember, id=staff_id, business=business)
    
    # Get all roles for this business
    all_roles = StaffRole.objects.filter(business=business, is_active=True)
    
    # Get staff availability
    weekly_availabilities = StaffAvailability.objects.filter(
        staff_member=staff,
        availability_type=AVAILABILITY_TYPE.WEEKLY
    ).order_by('weekday', 'start_time')
    
    specific_availabilities = StaffAvailability.objects.filter(
        staff_member=staff,
        availability_type=AVAILABILITY_TYPE.SPECIFIC,
        off_day=False
    ).order_by('specific_date', 'start_time')
    
    specific_off_days = StaffAvailability.objects.filter(
        staff_member=staff,
        availability_type=AVAILABILITY_TYPE.SPECIFIC,
        off_day=True
    ).order_by('specific_date')
    
    # Get weekly off days (days with no availability set)
    weekly_off_days = []
    for avail in weekly_availabilities:
        if avail.off_day and avail.weekday not in weekly_off_days:
            weekly_off_days.append(avail.weekday)
    
    # Get assigned bookings
    from bookings.models import BookingStaffAssignment
    assigned_bookings = BookingStaffAssignment.objects.filter(
        staff_member=staff
    ).select_related('booking', 'booking__lead', 'booking__service_offering').order_by('-booking__start_time')
    
    context = {
        'business': business,
        'staff': staff,
        'all_roles': all_roles,
        'weekly_availabilities': weekly_availabilities,
        'specific_availabilities': specific_availabilities,
        'specific_off_days': specific_off_days,
        'weekly_off_days': weekly_off_days,
        'assigned_bookings': assigned_bookings,
        'weekday_choices': WEEKDAY_CHOICES.choices,
    }
    
    return render(request, 'business/staff_detail.html', context)

@login_required
@require_http_methods(["POST"])
def update_staff(request, staff_id):
    """
    Update staff member information
    Handles form submission from the staff detail page
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
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
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        return JsonResponse({
            'success': False,
            'message': 'Please register your business first.'
        })
    
    business = request.user.business
    
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
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
    from bookings.models import StaffMember, StaffAvailability, AVAILABILITY_TYPE
    from django.utils.dateparse import parse_time, parse_date
    
    # Get staff member, ensuring it belongs to this business
    staff = get_object_or_404(StaffMember, id=staff_id, business=business)
    
    try:
        # Get form data
        availability_type = request.POST.get('availability_type')
        start_time = parse_time(request.POST.get('start_time'))
        end_time = parse_time(request.POST.get('end_time'))
        off_day = 'off_day' in request.POST
        
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
            specific_date = parse_date(request.POST.get('specific_date'))
            
            # Check if an availability already exists for this date and is not an off day
            existing_availabilities = StaffAvailability.objects.filter(
                staff_member=staff,
                availability_type=AVAILABILITY_TYPE.SPECIFIC,
                specific_date=specific_date
            )
            
            if existing_availabilities.exists() and not off_day:
                messages.warning(request, f'An availability for this date already exists. Please edit the existing one instead.')
                return redirect('business:staff_detail', staff_id=staff_id)
            
            # If it's an off day, we can have multiple (or replace existing)
            if off_day:
                # If marking as off day, remove any existing availabilities for this date
                existing_availabilities.delete()
            
            StaffAvailability.objects.create(
                staff_member=staff,
                availability_type=AVAILABILITY_TYPE.SPECIFIC,
                specific_date=specific_date,
                start_time=start_time,
                end_time=end_time,
                off_day=off_day
            )
            
            messages.success(request, 'Specific date availability added successfully!')
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
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
    from bookings.models import StaffMember, StaffAvailability
    from django.utils.dateparse import parse_time, parse_date
    
    # Get staff member, ensuring it belongs to this business
    staff = get_object_or_404(StaffMember, id=staff_id, business=business)
    
    try:
        # Get form data
        availability_id = request.POST.get('availability_id')
        start_time = parse_time(request.POST.get('start_time'))
        end_time = parse_time(request.POST.get('end_time'))
        off_day = 'off_day' in request.POST
        
        # Get the availability
        availability = get_object_or_404(StaffAvailability, id=availability_id, staff_member=staff)
        
        # Update availability
        availability.start_time = start_time
        availability.end_time = end_time
        availability.off_day = off_day
        
        # If it's a specific date availability, update the date
        if availability.availability_type == 'specific' and 'specific_date' in request.POST:
            availability.specific_date = parse_date(request.POST.get('specific_date'))
        
        availability.save()
        
        messages.success(request, 'Availability updated successfully!')
    except Exception as e:
        messages.error(request, f'Error updating availability: {str(e)}')
    
    return redirect('business:staff_detail', staff_id=staff_id)

@login_required
@require_http_methods(["POST"])
def delete_staff_availability(request):
    """
    Delete staff availability via AJAX
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        return JsonResponse({
            'success': False,
            'message': 'Please register your business first.'
        })
    
    business = request.user.business
    
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
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
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
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
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
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
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
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    business = request.user.business
    
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
def delete_staff_role(request):
    """
    Delete a staff role via AJAX
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        return JsonResponse({
            'success': False,
            'message': 'Please register your business first.'
        })
    
    business = request.user.business
    
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
