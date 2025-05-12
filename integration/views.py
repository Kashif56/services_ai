from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.urls import reverse
from django.template.defaultfilters import register
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import PlatformIntegration, DataMapping, IntegrationLog
from business.models import Business, BusinessConfiguration
from bookings.models import Booking
import json
from datetime import datetime, timedelta
from decimal import Decimal
from .utils import send_booking_data, create_mapped_payload, log_integration_activity
import requests
from django.conf import settings
# Create your views here.

@login_required
def integration_list(request):
    business = request.user.business
    if not business:
        return redirect('accounts:register_business')

    integrations = PlatformIntegration.objects.filter(business=business)
    return render(request, 'integrations/integration_list.html', {
        'integrations': integrations
    })

@login_required
def add_integration(request):
    if request.method == 'POST':
        name = request.POST.get('serviceName')
        platform_type = request.POST.get('platformType')
        
        integration_data = {
            'name': name,
            'platform_type': platform_type,
            'business': request.user.business,
            'is_active': True
        }

        if platform_type == 'direct_api':
            # Process custom headers if provided
            headers = {}
            header_keys = request.POST.getlist('header_key')
            header_values = request.POST.getlist('header_value')
            
            for i in range(len(header_keys)):
                if header_keys[i] and header_values[i]:  # Only add non-empty headers
                    headers[header_keys[i]] = header_values[i]
            
            integration_data.update({
                'base_url': request.POST.get('api_url'),
                'headers': headers
            })
        else:  # workflow platform
            integration_data.update({
                'webhook_url': request.POST.get('webhook_url'),
            })

        # Create new integration
        integration = PlatformIntegration.objects.create(**integration_data)

      
        messages.success(request, 'Integration added successfully!')
        if platform_type == 'direct_api':
            return redirect('integration:integration_mapping', platform_id=integration.id)
        return redirect('integration:integration_list')

    context = {
        'platform_types': dict(PlatformIntegration.PLATFORM_TYPE_CHOICES),
        'integration': None
    }
    
    return render(request, 'integrations/add_integration.html', context)

@login_required
def edit_integration(request, platform_id):
    integration = get_object_or_404(PlatformIntegration, id=platform_id, business=request.user.business)
    
    if request.method == 'POST':
        # Update basic information
        integration.name = request.POST.get('serviceName')
        
        # Update platform-specific information
        if integration.platform_type == 'direct_api':
            integration.base_url = request.POST.get('api_url')
            
            # Process custom headers
            headers = {}
            header_keys = request.POST.getlist('header_key')
            header_values = request.POST.getlist('header_value')
            
            for i in range(len(header_keys)):
                if header_keys[i] and header_values[i]:  # Only add non-empty headers
                    headers[header_keys[i]] = header_values[i]
            
            integration.headers = headers
        else:  # workflow
            integration.webhook_url = request.POST.get('webhook_url')
        
        integration.save()
        messages.success(request, 'Integration updated successfully!')
        return redirect('integration:integration_list')
    
    context = {
        'platform_types': dict(PlatformIntegration.PLATFORM_TYPE_CHOICES),
        'integration': integration,
        'headers': integration.headers or {}
    }
    
    return render(request, 'integrations/add_integration.html', context)

@login_required
def integration_mapping(request, platform_id):
    platform = get_object_or_404(PlatformIntegration, id=platform_id, business=request.user.business)
    
    # If it's a workflow platform, redirect to integration list
    if platform.platform_type == 'workflow':
        messages.info(request, 'Workflow platforms do not require field mapping.')
        return redirect('integration:integration_list')
        
    mappings = DataMapping.objects.filter(platform=platform)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        mappings_data = data.get('mappings', [])
        
        # Delete existing mappings
        DataMapping.objects.filter(platform=platform).delete()
        
        # Create new mappings
        for mapping_data in mappings_data:
            DataMapping.objects.create(
                platform=platform,
                source_field=mapping_data['source_field'],
                target_field=mapping_data['target_field'],
                parent_path=mapping_data.get('parent_path'),
                field_type=mapping_data.get('field_type', 'string'),
                default_value=mapping_data.get('default_value', ''),
                is_required=mapping_data.get('is_required', False)
            )
        
        return JsonResponse({'status': 'success'})

    # Get all available fields from Booking model and business configuration
    # First, get fields from the actual model
    available_fields = []
    
    # Add Booking model fields
    for field in Booking._meta.get_fields():
        # Add regular fields
        if hasattr(field, 'attname') and not field.is_relation:
            available_fields.append(f"booking.{field.attname}")
        # Add only essential foreign key fields
        elif field.is_relation and field.many_to_one and field.name in ['service_offering', 'business', 'lead']:
            relation_name = field.name
            available_fields.append(f"booking.{relation_name}_id")
            available_fields.append(f"booking.{relation_name}_name")
    
    # Add service item fields with their identifiers
    from business.models import ServiceItem
    
    # Get all service items for this business
    service_items = ServiceItem.objects.filter(business=request.user.business, is_active=True)
    
    for item in service_items:
        identifier = item.identifier or f"item_{item.id}"
        
        # Add the three key fields for each service item
        available_fields.append(f"{identifier}.quantity")
        available_fields.append(f"{identifier}.price")
        available_fields.append(f"{identifier}.selected")
            
    # Then add any custom fields from business configuration
    business_config = BusinessConfiguration.objects.filter(business=request.user.business).first()
    if business_config and hasattr(business_config, 'form_fields'):
        if business_config.form_fields:
            for field in business_config.form_fields:
                field_name = field.get('name')
                if field_name:
                    custom_field_name = f"custom.{field_name}"
                    if custom_field_name not in available_fields:
                        available_fields.append(custom_field_name)

    field_types = [
        ('string', 'Text'),
        ('number', 'Number'),
        ('boolean', 'True/False'),
        ('date', 'Date'),
        ('time', 'Time'),
        ('datetime', 'Date & Time'),
        ('array', 'Array/List'),
        ('object', 'Object')
    ]

    context = {
        'platform': platform,
        'mappings': mappings,
        'available_fields': available_fields,
        'field_types': field_types
    }

    return render(request, 'integrations/mapping.html', context)

@login_required
def preview_mapping(request, platform_id):
    platform = get_object_or_404(PlatformIntegration, id=platform_id, business=request.user.business)
    mappings = DataMapping.objects.filter(platform=platform)
    
    # Get a sample booking
    sample_booking = Booking.objects.filter(business=request.user.business).first()
    
    # Prepare sample data with categorized fields
    sample_data = {}
    
    # Booking data
    if sample_booking:
        booking_data = {}
        
        # Add regular fields
        for field in sample_booking._meta.get_fields():
            if hasattr(field, 'attname') and not field.is_relation:
                field_name = field.attname
                value = getattr(sample_booking, field_name, None)
                
                # Handle special types like Decimal, datetime, etc.
                if isinstance(value, Decimal):
                    value = float(value)
               
                elif isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
               
                
                booking_data[field_name] = value
        
        # Add only essential foreign key fields
        # Service offering
        if sample_booking.service_offering:
            booking_data['service_offering_id'] = sample_booking.service_offering.id
            booking_data['service_offering_name'] = sample_booking.service_offering.name
        else:
            booking_data['service_offering_id'] = None
            booking_data['service_offering_name'] = None
            
        # Business
        if sample_booking.business:
            booking_data['business_id'] = sample_booking.business.id
            booking_data['business_name'] = sample_booking.business.name
        else:
            booking_data['business_id'] = None
            booking_data['business_name'] = None
            
        # Lead
        if sample_booking.lead:
            booking_data['lead_id'] = sample_booking.lead.id
            booking_data['lead_name'] = sample_booking.lead.name
        else:
            booking_data['lead_id'] = None
            booking_data['lead_name'] = None
        
        sample_data['booking'] = booking_data
        
        # Add service items with their identifiers
        from bookings.models import BookingServiceItem
        from business.models import ServiceItem
        
        # Get all service items for this business
        all_service_items = ServiceItem.objects.filter(business=request.user.business, is_active=True)
        
        # Get booked service items if available
        booked_items = {}
        if sample_booking:
            booking_service_items = BookingServiceItem.objects.filter(booking=sample_booking).select_related('service_item')
            for item in booking_service_items:
                if item.service_item:
                    booked_items[item.service_item.id] = {
                        'quantity': item.quantity,
                        'price': item.service_item.price_value,
                        'selected': True
                    }
        
        # Add all service items to sample data
        for item in all_service_items:
            identifier = item.identifier or f"item_{item.id}"
            
            # If this item was booked, use the booking data
            if item.id in booked_items:
                sample_data[identifier] = {
                    'quantity': booked_items[item.id]['quantity'],
                    'price': booked_items[item.id]['price'],
                    'selected': True
                }
            else:
                # Otherwise use default values
                sample_data[identifier] = {
                    'quantity': 0,
                    'price': item.price_value,
                    'selected': False
                }
            
            # No longer adding service item info data as it's not displayed
    else:
        # Create a dummy booking data for preview if none exists
        sample_data = {
            'id': 1,
            'firstName': "John",
            'lastName': "Doe",
            'email': "john@example.com",
            'phoneNumber': "123-456-7890",
            'address1': "123 Main St",
            'city': "Sample City",
            'stateOrProvince': "State",
            'zipCode': "12345",
            'serviceType': "standard",
            'cleaningDate': "2025-03-01",
            'totalPrice': "150.00",
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'business_id': request.user.business.id
        }
        
        # Add dynamic fields based on business configuration
        business_config = BusinessConfiguration.objects.filter(business=request.user.business).first()
        if business_config:
            if hasattr(business_config, 'form_fields') and business_config.form_fields:
                for field in business_config.form_fields:
                    field_name = field.get('name')
                    field_type = field.get('type')
                    
                    if field_name:
                        if field_type == 'number':
                            sample_data[field_name] = 1
                        elif field_type == 'checkbox':
                            sample_data[field_name] = True
                        else:
                            sample_data[field_name] = f"Sample {field_name}"

    # Generate mapped data
    mapped_data = {}
    required_fields = set()
    
    # Group mappings by type (flat vs nested)
    grouped_mappings = {
        'Flat': [],
        'Nested': []
    }
    
    for mapping in mappings:
        # Get value from sample data or use default value
        value = sample_data.get(mapping.source_field, mapping.default_value)
        
        # Track required fields
        if mapping.is_required:
            required_fields.add(mapping.source_field)
        
        # Handle nested paths
        if mapping.parent_path:
            path_parts = mapping.parent_path.split('.')
            current_dict = mapped_data
            
            # Create nested structure
            for part in path_parts:
                if part not in current_dict:
                    current_dict[part] = {}
                current_dict = current_dict[part]
            
            current_dict[mapping.target_field] = value
            grouped_mappings['Nested'].append(mapping)
        else:
            mapped_data[mapping.target_field] = value
            grouped_mappings['Flat'].append(mapping)

    # Remove empty groups
    grouped_mappings = {k: v for k, v in grouped_mappings.items() if v}

    # Get all available fields for the dropdown
    available_fields = list(sample_data.keys())

    # Create the mapped payload
    mapped_data = create_mapped_payload(sample_data, platform)
    
    # Group mappings by parent_path
    grouped_mappings = {
        'Nested': [m for m in mappings if m.parent_path],
        'Flat': [m for m in mappings if not m.parent_path]
    }
    
    # Get headers for display
    headers = platform.headers or {}
    
    context = {
        'platform': platform,
        'mappings': mappings,
        'grouped_mappings': grouped_mappings,
        'sample_data': sample_data,
        'mapped_data': mapped_data,
        'headers': headers,
        'required_fields': required_fields,
        'available_fields': available_fields
    }

    return render(request, 'integrations/preview_mapping.html', context)




@login_required
@require_POST
def test_integration(request, platform_id):
    """Test an integration by sending sample data"""
    try:
        integration = get_object_or_404(
            PlatformIntegration, 
            id=platform_id, 
            business=request.user.business
        )

        # Get a sample booking from the database
        sample_booking = Booking.objects.filter(business=request.user.business).first()
        
        if not sample_booking:
            return JsonResponse({
                'success': False,
                'message': 'No bookings found to use as test data. Please create a booking first.'
            }, status=400)
        
        # Prepare sample data with categorized fields - using the same structure as in preview_mapping
        sample_data = {}
        
        # Booking data
        booking_data = {}
        
        # Add regular fields
        for field in sample_booking._meta.get_fields():
            if hasattr(field, 'attname') and not field.is_relation:
                field_name = field.attname
                value = getattr(sample_booking, field_name, None)
                
                # Handle special types like Decimal, datetime, etc.
                if isinstance(value, Decimal):
                    value = float(value)
                elif isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                
                booking_data[field_name] = value
        
        # Add only essential foreign key fields
        # Service offering
        if sample_booking.service_offering:
            booking_data['service_offering_id'] = sample_booking.service_offering.id
            booking_data['service_offering_name'] = sample_booking.service_offering.name
        else:
            booking_data['service_offering_id'] = None
            booking_data['service_offering_name'] = None
            
        # Business
        if sample_booking.business:
            booking_data['business_id'] = sample_booking.business.id
            booking_data['business_name'] = sample_booking.business.name
        else:
            booking_data['business_id'] = None
            booking_data['business_name'] = None
            
        # Lead
        if sample_booking.lead:
            booking_data['lead_id'] = sample_booking.lead.id
            booking_data['lead_name'] = sample_booking.lead.name
        else:
            booking_data['lead_id'] = None
            booking_data['lead_name'] = None
        
        sample_data['booking'] = booking_data
        
        # Add service items with their identifiers
        from bookings.models import BookingServiceItem
        from business.models import ServiceItem
        
        # Get all service items for this business
        all_service_items = ServiceItem.objects.filter(business=request.user.business, is_active=True)
        
        # Get booked service items if available
        booked_items = {}
        booking_service_items = BookingServiceItem.objects.filter(booking=sample_booking).select_related('service_item')
        for item in booking_service_items:
            if item.service_item:
                booked_items[item.service_item.id] = {
                    'quantity': item.quantity,
                    'price': item.service_item.price_value,
                    'selected': True
                }
        
        # Add all service items to sample data
        for item in all_service_items:
            identifier = item.identifier or f"item_{item.id}"
            
            # If this item was booked, use the booking data
            if item.id in booked_items:
                sample_data[identifier] = {
                    'quantity': booked_items[item.id]['quantity'],
                    'price': booked_items[item.id]['price'],
                    'selected': True
                }
            else:
                # Otherwise use default values
                sample_data[identifier] = {
                    'quantity': 0,
                    'price': item.price_value,
                    'selected': False
                }
        
        # Use this real data structure for testing
        test_data = sample_data

        # Send test data only to this specific integration
        test_results = send_booking_data_to_integration(test_data, integration)
        
        if test_results.get('success', []):
            return JsonResponse({
                'success': True,
                'message': 'Test data sent successfully!',
                'response': test_results['success'][0]  # Get the first success response
            })
        else:
            error_msg = test_results.get('failed', [{}])[0].get('error', 'Unknown error occurred')
            return JsonResponse({
                'success': False,
                'message': f'Failed to send test data: {error_msg}'
            }, status=400)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print("Test Integration Error:", error_details)  # Log the full error
        return JsonResponse({
            'success': False,
            'message': f'Error testing integration: {str(e)}'
        }, status=500)

def send_booking_data_to_integration(booking_data, integration):
    """Send booking data to a specific integration"""
    try:
        results = {
            'success': [],
            'failed': []
        }

        if integration.platform_type == 'workflow':
            # Process booking data to ensure it's in the right format
            processed_data = {}
            
            # Handle datetime fields if they exist
            cleaning_date_field = next((f for f in ['cleaningDateTime', 'cleaningDate', 'appointmentDate', 'booking_date'] 
                                     if f in booking_data), None)
            
            if cleaning_date_field and isinstance(booking_data[cleaning_date_field], datetime):
                cleaning_date = booking_data[cleaning_date_field].date().isoformat()
                cleaning_time = booking_data[cleaning_date_field].time().strftime("%H:%M:%S")
                # Calculate end time (1 hour after start time by default)
                end_time = (booking_data[cleaning_date_field] + timedelta(minutes=60)).time().strftime("%H:%M:%S")
                
                processed_data["cleaningDate"] = cleaning_date
                processed_data["startTime"] = cleaning_time
                processed_data["endTime"] = end_time
            
            # Copy all other fields from booking_data to processed_data
            for key, value in booking_data.items():
                # Skip the already processed datetime field
                if key == cleaning_date_field:
                    continue
                    
                # Handle special types
                if isinstance(value, Decimal):
                    processed_data[key] = float(value)
                elif isinstance(value, datetime):
                    processed_data[key] = value.isoformat()
                else:
                    processed_data[key] = value
            
            # Use the processed data as the payload
            payload = processed_data
            
            try:
                response = requests.post(
                    integration.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )

                # Safely parse JSON response
                response_data = None
                if response.text:
                    try:
                        response_data = response.json()
                    except json.JSONDecodeError:
                        # If response is not valid JSON, use text as is
                        response_data = {"raw_response": response.text}

                if response.status_code in [200, 201]:
                    log_integration_activity(
                        platform=integration,
                        status='success',
                        request_data=payload,
                        response_data=response_data
                    )
                else:
                    log_integration_activity(
                        platform=integration,
                        status='failed',
                        request_data=payload,
                        error_message=response.text
                    )
                
                results['success'].append({
                    'name': integration.name,
                    'response': response.text,
                    'status_code': response.status_code
                })
                
            except requests.RequestException as req_err:
                error_msg = f"Request error: {str(req_err)}"
                log_integration_activity(
                    platform=integration,
                    status='failed',
                    request_data=payload,
                    error_message=error_msg
                )
                
                results['failed'].append({
                    'name': integration.name,
                    'error': error_msg
                })
            
        else:  # direct_api
            # Process booking data to ensure it's in the right format for mapping
            from datetime import date, time
            import json
            
            # Helper function to recursively process data and handle date/time objects
            def process_data(data):
                if isinstance(data, dict):
                    return {k: process_data(v) for k, v in data.items()}
                elif isinstance(data, list):
                    return [process_data(item) for item in data]
                elif isinstance(data, Decimal):
                    return float(data)
                elif isinstance(data, datetime):
                    return data.isoformat()
                elif isinstance(data, date):
                    return data.isoformat()
                elif isinstance(data, time):
                    return data.isoformat()
                else:
                    return data
            
            # Process all data recursively
            processed_data = process_data(booking_data)
                    
            # Use the create_mapped_payload function from utils.py
            from .utils import create_mapped_payload
            payload = create_mapped_payload(processed_data, integration)
            print("Payload:", payload)
            
            # Start with default headers
            headers = {"Content-Type": "application/json"}
            
            # Add custom headers from integration
            if integration.headers:
                headers.update(integration.headers)
            
            print("Headers:", headers)
            
            try:
                response = requests.post(
                    integration.base_url,
                    json=payload,
                    headers=headers,
                    timeout=30
                )

                print("Response:", response)

                # Safely parse JSON response
                response_data = None
                if response.text:
                    try:
                        response_data = response.json()
                    except json.JSONDecodeError:
                        # If response is not valid JSON, use text as is
                        response_data = {"raw_response": response.text}

                if response.status_code in [200, 201]:
                    log_integration_activity(
                        platform=integration,
                        status='success',
                        request_data=payload,
                        response_data=response_data
                    )
                else:
                    log_integration_activity(
                        platform=integration,
                        status='failed',
                        request_data=payload,
                        error_message=response.text
                    )
                
                results['success'].append({
                    'name': integration.name,
                    'response': response.text,
                    'status_code': response.status_code
                })
                
            except requests.RequestException as req_err:
                error_msg = f"Request error: {str(req_err)}"
                log_integration_activity(
                    platform=integration,
                    status='failed',
                    request_data=payload,
                    error_message=error_msg
                )
                
                results['failed'].append({
                    'name': integration.name,
                    'error': error_msg
                })
        
        return results

    except Exception as e:
        # Log failed integration
        log_integration_activity(
            platform=integration,
            status='failed',
            request_data=payload if 'payload' in locals() else {},
            error_message=str(e)
        )
        
        return {
            'success': [],
            'failed': [{
                'name': integration.name,
                'error': str(e)
            }]
        }

@login_required
def edit_integration(request, platform_id):
    platform = get_object_or_404(PlatformIntegration, id=platform_id, business=request.user.business)
    
    if request.method == 'POST':
        name = request.POST.get('serviceName')
        platform_type = request.POST.get('platformType')
        is_active = request.POST.get('is_active') == 'on'
        
        # Update basic fields
        platform.name = name
        platform.platform_type = platform_type
        platform.is_active = is_active
        
        # Update type-specific fields
        if platform_type == 'direct_api':
            platform.base_url = request.POST.get('api_url')
            platform.auth_type = 'token'  # Default to token auth
            
            # Only update the token if a new one is provided
            api_key = request.POST.get('api_key')
            if api_key:
                platform.auth_data = {'token': api_key}
                
            # Clear webhook URL if switching from workflow to direct API
            platform.webhook_url = ''
        else:  # workflow platform
            platform.webhook_url = request.POST.get('webhook_url')
            platform.auth_type = 'none'
            
            # Clear API-specific fields if switching from direct API to workflow
            platform.base_url = ''
            platform.auth_data = {}
        
        platform.save()
        messages.success(request, 'Integration updated successfully!')
        
        if platform_type == 'direct_api':
            return redirect('integration:integration_mapping', platform_id=platform.id)
        return redirect('integration:integration_list')
       
    # Get choices from model
    platform_types = dict(PlatformIntegration.PLATFORM_TYPE_CHOICES)
    
    return render(request, 'integrations/edit_integration.html', {
        'integration': platform,
        'platform_types': platform_types,
    })

@login_required
def delete_integration(request, platform_id):
    platform = get_object_or_404(PlatformIntegration, id=platform_id, business=request.user.business)
    if request.method == 'POST':
        platform.delete()
        messages.success(request, 'Integration deleted successfully!')
        return redirect('integration:integration_list')
    
    return render(request, 'integrations/delete_confirmation.html', {
        'platform': platform
    })


@login_required
def save_field_mappings(request, integration_id):
    if request.method == 'POST':
        try:
            integration = get_object_or_404(PlatformIntegration, id=integration_id)
            data = json.loads(request.body)
            mappings = data.get('mappings', [])

            # Delete existing mappings
            DataMapping.objects.filter(platform=integration).delete()

            # Create new mappings
            for mapping in mappings:
                DataMapping.objects.create(
                    platform=integration,
                    source_field=mapping['source_field'],
                    target_field=mapping['target_field']
                )

            return JsonResponse({
                'success': True,
                'message': 'Mappings saved successfully',
                'redirect_url': reverse('integration:integration_list')
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })

    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })



@login_required
def integration_logs(request, platform_id=None):
    """View integration logs for all integrations or a specific one"""
    business = request.user.business
    if not business:
        return redirect('business:register')
        
    # Get query parameters for filtering
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base query - filter by business
    if platform_id:
        # For a specific integration
        platform = get_object_or_404(PlatformIntegration, id=platform_id, business=business)
        logs_query = IntegrationLog.objects.filter(platform=platform)
        # Set the title accordingly
        title = f"Integration Logs: {platform.name}"
    else:
        # For all integrations of this business
        platforms = PlatformIntegration.objects.filter(business=business)
        logs_query = IntegrationLog.objects.filter(platform__in=platforms)
        title = "All Integration Logs"
    
    # Apply filters if provided
    if status_filter:
        logs_query = logs_query.filter(status=status_filter)
        
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            logs_query = logs_query.filter(created_at__gte=date_from_obj)
        except ValueError:
            pass  # Invalid date format
            
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            # Add one day to include the end date
            date_to_obj = date_to_obj + timedelta(days=1)
            logs_query = logs_query.filter(created_at__lt=date_to_obj)
        except ValueError:
            pass  # Invalid date format
    
    # Get logs with pagination (20 logs per page)
    paginator = Paginator(logs_query.order_by('-created_at'), 20)
    page = request.GET.get('page')
    try:
        logs = paginator.page(page)
    except PageNotAnInteger:
        logs = paginator.page(1)
    except EmptyPage:
        logs = paginator.page(paginator.num_pages)
    
    # Get all integrations for the filter dropdown
    integrations = PlatformIntegration.objects.filter(business=business)
    
    # Get stats
    total_logs = logs_query.count()
    success_logs = logs_query.filter(status='success').count()
    failed_logs = logs_query.filter(status='failed').count()
    pending_logs = logs_query.filter(status='pending').count()
    
    context = {
        'logs': logs,
        'integrations': integrations,
        'platform_id': platform_id,
        'status_filter': status_filter, 
        'date_from': date_from,
        'date_to': date_to,
        'title': title,
        'status_choices': dict(IntegrationLog.STATUS_CHOICES),
        'paginator': paginator,
        'total_logs': total_logs,
        'success_logs': success_logs,
        'failed_logs': failed_logs,
        'pending_logs': pending_logs
    }
    
    return render(request, 'integrations/integration_logs.html', context)

# Template filter for pretty printing JSON data
@register.filter
def pprint(data):
    if isinstance(data, dict) or isinstance(data, list):
        return json.dumps(data, indent=2)
    return data
