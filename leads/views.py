from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from django.contrib import messages
from .models import Lead, LeadStatus, LeadSource
from business.models import Business
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import logging
import uuid
from .webhook_processors import get_processor, autodiscover_processors, register_processor
# Import webhook processors directly
from .webhook_processors.zoho import ZohoWebhookProcessor
try:
    from .webhook_processors.hubspot import HubSpotWebhookProcessor
    from .webhook_processors.salesforce import SalesforceWebhookProcessor
    from .webhook_processors.pipedrive import PipedriveWebhookProcessor
    from .webhook_processors.monday import MondayWebhookProcessor
except ImportError:
    print("Some webhook processors could not be imported")

logger = logging.getLogger(__name__)

# Auto-discover webhook processors
autodiscover_processors()

# Direct registration of webhook processors
print("Directly registering webhook processors...")
register_processor('zoho', ZohoWebhookProcessor)
try:
    register_processor('hubspot', HubSpotWebhookProcessor)
    register_processor('salesforce', SalesforceWebhookProcessor)
    register_processor('pipedrive', PipedriveWebhookProcessor)
    register_processor('monday', MondayWebhookProcessor)
    print("All webhook processors registered directly")
except NameError:
    print("Some webhook processors could not be registered")

@login_required
def index(request):
    # Get the user's business
    business = request.user.business
    
    # Get filter parameters
    status = request.GET.get('status', '')
    source = request.GET.get('source', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('search', '')
    
    # Start with all leads for the business
    leads = Lead.objects.filter(business=business)
    
    # Apply filters
    if status:
        leads = leads.filter(status=status)
    
    if source:
        leads = leads.filter(source=source)
    
    if date_from:
        leads = leads.filter(created_at__gte=date_from)
    
    if date_to:
        # Add one day to include the end date
        leads = leads.filter(created_at__lte=date_to + ' 23:59:59')
    
    if search_query:
        leads = leads.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    context = {
        'leads': leads,
        'lead_statuses': LeadStatus.choices,
        'lead_sources': LeadSource.choices,
        'current_status': status,
        'current_source': source,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
    }
    
    return render(request, 'leads/index.html', context)

@login_required
def lead_detail(request, lead_id):
    # Get the user's business
    business = request.user.business
    
    # Get the lead, ensuring it belongs to the user's business
    lead = get_object_or_404(Lead, id=lead_id, business=business)
    
    # Get all communications for this lead
    communications = lead.communications.all().order_by('-created_at')
    
    # Get all fields for this lead
    lead_fields = lead.fields.all().select_related('field')
    
    context = {
        'lead': lead,
        'communications': communications,
        'lead_fields': lead_fields,
        'lead_statuses': LeadStatus.choices,
    }
    
    return render(request, 'leads/detail.html', context)

@login_required
def create_lead(request):
    # Get the user's business
    business = request.user.business
    
    if request.method == 'POST':
        # Extract basic lead information
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        status = request.POST.get('status')
        source = request.POST.get('source')
        notes = request.POST.get('notes')
        
        # Create the lead
        lead = Lead.objects.create(
            business=business,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            status=status,
            source=source,
            notes=notes
        )
        
        messages.success(request, 'Lead created successfully!')
        return redirect('leads:lead_detail', lead_id=lead.id)
    
    # Provide a limited set of the most relevant statuses for new leads
    limited_statuses = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('qualified', 'Qualified'),
        ('appointment_scheduled', 'Appointment Scheduled')
    ]
    
    # Provide a limited set of the most common lead sources
    limited_sources = [
        ('website', 'Website'),
        ('phone', 'Phone Call'),
        ('referral', 'Referral'),
        ('social_media', 'Social Media'),
        ('other', 'Other')
    ]
    
    context = {
        'lead_statuses': limited_statuses,
        'lead_sources': limited_sources,
    }
    
    return render(request, 'leads/create.html', context)

@login_required
def edit_lead(request, lead_id):
    # Get the user's business
    business = request.user.business
    
    # Get the lead, ensuring it belongs to the user's business
    lead = get_object_or_404(Lead, id=lead_id, business=business)
    
    # Provide a limited set of the most relevant statuses for leads
    limited_statuses = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('qualified', 'Qualified'),
        ('appointment_scheduled', 'Appointment Scheduled'),
        ('converted', 'Converted'),
        ('lost', 'Lost')
    ]
    
    # Provide a limited set of the most common lead sources
    limited_sources = [
        ('website', 'Website'),
        ('phone', 'Phone Call'),
        ('referral', 'Referral'),
        ('social_media', 'Social Media'),
        ('other', 'Other')
    ]
    
    if request.method == 'POST':
        # Extract updated lead information
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        status = request.POST.get('status')
        source = request.POST.get('source')
        notes = request.POST.get('notes')
        
        # Update the lead
        lead.first_name = first_name
        lead.last_name = last_name
        lead.email = email
        lead.phone = phone
        lead.status = status
        lead.source = source
        lead.notes = notes
        lead.save()
        
        messages.success(request, 'Lead updated successfully!')
        return redirect('leads:lead_detail', lead_id=lead.id)
    
    context = {
        'lead': lead,
        'lead_statuses': limited_statuses,
        'lead_sources': limited_sources,
        'is_edit': True
    }
    
    return render(request, 'leads/edit.html', context)

@csrf_exempt
@require_POST
def webhook_receiver(request, lead_source, business_id):
    """
    Main webhook receiver view that handles incoming webhooks from different CRM systems.
    
    Args:
        request: The Django HttpRequest object
        lead_source: The CRM source identifier (e.g., 'hubspot', 'salesforce')
        business_id: The UUID of the business this webhook is for
    
    Returns:
        HttpResponse: The response to send back to the webhook sender
    """
    print(f"Received webhook from {lead_source} for business {business_id}")
    print(f"Request body: {request.body}")
    print(f"Content type: {request.content_type}")
    
    try:
        # Get the appropriate webhook processor for this source
        try:
            # Force lowercase for consistent matching
            processor = get_processor(lead_source.lower())
            print(f"Found processor for {lead_source}: {processor.__class__.__name__}")
        except KeyError:
            print(f"No webhook processor found for source: {lead_source}")
            # Attempt to reload webhook processors
            autodiscover_processors()
            
            # Try one more time
            try:
                processor = get_processor(lead_source.lower())
                print(f"Successfully loaded processor for {lead_source} after rediscovery")
            except KeyError:
                # Last resort: direct registration
                if lead_source.lower() == 'zoho':
                    print("Directly registering Zoho processor as last resort")
                    from .webhook_processors.zoho import ZohoWebhookProcessor
                    register_processor('zoho', ZohoWebhookProcessor)
                    processor = get_processor('zoho')
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Unsupported lead source: {lead_source}'
                    }, status=400)
        
        # Process the webhook
        print(f"Processing webhook with {processor.__class__.__name__}")
        response = processor.process_webhook(request, business_id)
        print(f"Webhook processing completed with status: {response.status_code}")
        return response
        
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Error processing webhook: {str(e)}'
        }, status=500)
