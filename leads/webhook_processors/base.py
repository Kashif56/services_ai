"""
Base webhook processor class that all CRM-specific processors will inherit from.
"""
from abc import ABC, abstractmethod
import json
import logging
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from ..models import Lead, LeadStatus, LeadSource, WebhookLog

logger = logging.getLogger(__name__)

class WebhookProcessor(ABC):
    """
    Abstract base class for all webhook processors.
    Each CRM system should implement its own processor by extending this class.
    """
    
    # Source identifier for this processor (to be overridden by subclasses)
    source_id = None
    
    # Human-readable name for this processor
    name = None
    
    def __init__(self):
        if not self.source_id or not self.name:
            raise ValueError("Webhook processor must define source_id and name")
    
    def process_webhook(self, request, business_id):
        """
        Process an incoming webhook request.
        
        Args:
            request: The Django HttpRequest object
            business_id: The UUID of the business this webhook is for
            
        Returns:
            HttpResponse: The response to send back to the webhook sender
        """
        try:
            # Parse the request data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
            
            # Validate the webhook data
            is_valid, validation_message = self.validate_webhook(data, business_id)
            if not is_valid:
                logger.warning(f"Invalid webhook data from {self.name}: {validation_message}")
                return JsonResponse({
                    'status': 'error',
                    'message': validation_message
                }, status=400)
            
            # Process the webhook data to extract lead information
            lead_data = self.extract_lead_data(data)
            
            # Create or update the lead
            lead = self.create_or_update_lead(lead_data, business_id)
            
            # Log the webhook
            self.log_webhook(request, data, lead, business_id, 200)
            
            # Return a success response
            return JsonResponse({
                'status': 'success',
                'message': 'Webhook processed successfully',
                'lead_id': str(lead.id)
            })
            
        except Exception as e:
            logger.exception(f"Error processing webhook from {self.name}: {str(e)}")
            # Log the webhook error
            self.log_webhook(request, data if 'data' in locals() else {}, None, business_id, 500)
            
            # Return an error response
            return JsonResponse({
                'status': 'error',
                'message': f'Error processing webhook: {str(e)}'
            }, status=500)
    
    @abstractmethod
    def validate_webhook(self, data, business_id):
        """
        Validate the webhook data.
        
        Args:
            data: The parsed webhook data
            business_id: The UUID of the business this webhook is for
            
        Returns:
            tuple: (is_valid, message) - A boolean indicating if the data is valid and a message
        """
        pass
    
    @abstractmethod
    def extract_lead_data(self, data):
        """
        Extract lead information from the webhook data.
        
        Args:
            data: The parsed webhook data
            
        Returns:
            dict: A dictionary containing the lead data with standardized keys
        """
        pass
    
    def create_or_update_lead(self, lead_data, business_id):
        """
        Create a new lead or update an existing one based on the webhook data.
        
        Args:
            lead_data: The extracted lead data
            business_id: The UUID of the business this lead belongs to
            
        Returns:
            Lead: The created or updated Lead object
        """
        from business.models import Business
        
        # Get the business
        business = Business.objects.get(id=business_id)
        
        # Check if the lead already exists (by email)
        email = lead_data.get('email')
        if email:
            try:
                lead = Lead.objects.get(business=business, email=email)
                # Update existing lead
                lead.first_name = lead_data.get('first_name', lead.first_name)
                lead.last_name = lead_data.get('last_name', lead.last_name)
                lead.phone = lead_data.get('phone', lead.phone)
                lead.source = lead_data.get('source', lead.source)
                lead.notes = lead_data.get('notes', lead.notes)
                lead.updated_at = timezone.now()
                lead.save()
                
                logger.info(f"Updated existing lead: {lead.id}")
                
            except Lead.DoesNotExist:
                # Create new lead
                lead = Lead.objects.create(
                    business=business,
                    first_name=lead_data.get('first_name', ''),
                    last_name=lead_data.get('last_name', ''),
                    email=email,
                    phone=lead_data.get('phone', ''),
                    status=LeadStatus.NEW,
                    source=lead_data.get('source', LeadSource.WEBSITE),
                    notes=lead_data.get('notes', '')
                )
                
                logger.info(f"Created new lead: {lead.id}")
        else:
            # Create new lead without email
            lead = Lead.objects.create(
                business=business,
                first_name=lead_data.get('first_name', ''),
                last_name=lead_data.get('last_name', ''),
                email='',
                phone=lead_data.get('phone', ''),
                status=LeadStatus.NEW,
                source=lead_data.get('source', LeadSource.WEBSITE),
                notes=lead_data.get('notes', '')
            )
            
            logger.info(f"Created new lead without email: {lead.id}")
        
        # Add any custom fields if they exist
        custom_fields = lead_data.get('custom_fields', {})
        if custom_fields and hasattr(business, 'industry') and business.industry:
            from ..models import LeadField
            
            for field_name, field_value in custom_fields.items():
                try:
                    # Try to find the industry field
                    industry_field = business.industry.fields.get(slug=field_name)
                    
                    # Create or update the lead field
                    LeadField.objects.update_or_create(
                        lead=lead,
                        field=industry_field,
                        defaults={'value': field_value}
                    )
                except Exception as e:
                    logger.warning(f"Could not save custom field {field_name}: {str(e)}")
        
        return lead
    
    def log_webhook(self, request, data, lead, business_id, status_code):
        """
        Log the webhook request for auditing and debugging.
        
        Args:
            request: The Django HttpRequest object
            data: The parsed webhook data
            lead: The Lead object that was created or updated (or None if error)
            business_id: The UUID of the business this webhook is for
            status_code: The HTTP status code of the response
        """
        from business.models import Business
        from ..models import WebhookEndpoint, WebhookLog
        
        try:
            # Get the business
            business = Business.objects.get(id=business_id)
            
            # Get or create a webhook endpoint for this source
            endpoint, _ = WebhookEndpoint.objects.get_or_create(
                business=business,
                name=self.name,
                slug=self.source_id,
                defaults={
                    'is_active': True,
                    'field_mapping': {}
                }
            )
            
            # Create the webhook log
            WebhookLog.objects.create(
                endpoint=endpoint,
                request_data=data,
                response_data={
                    'status_code': status_code,
                    'lead_id': str(lead.id) if lead else None
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                status_code=status_code,
                lead=lead
            )
            
        except Exception as e:
            logger.exception(f"Error logging webhook: {str(e)}")
