"""
Zoho CRM webhook processor for handling incoming webhook requests from Zoho CRM.
"""
import json
from django.http import JsonResponse
from .base import WebhookProcessor
from ..models import LeadSource, Lead, LeadStatus
from urllib.parse import unquote_plus
from django.utils import timezone

class ZohoWebhookProcessor(WebhookProcessor):
    """
    Webhook processor for Zoho CRM.
    Handles lead creation and update events from Zoho CRM.
    """
    source_id = 'zoho'
    name = 'Zoho CRM'
    
    def validate_webhook(self, data, business_id):
        """
        Validate the webhook data from Zoho CRM.
        
        Zoho webhooks can come in two formats:
        1. JSON format with module, token, and data fields
        2. Form-encoded format with direct field values
        
        Args:
            data: The parsed webhook data
            business_id: The UUID of the business this webhook is for
            
        Returns:
            tuple: (is_valid, message) - A boolean indicating if the data is valid and a message
        """
        print(f"Validating Zoho webhook data: {data}")
        
        # Check if this is form-encoded data (direct field values)
        if 'first_name' in data or 'last_name' in data or 'email' in data or 'phone_number' in data:
            # Form-encoded data is valid if it has at least one of these fields
            return True, "Valid webhook data (form-encoded)"
        
        # Otherwise, check if this is JSON format
        if 'module' not in data:
            return False, "Missing required field: module"
        
        # Check if this is a lead or contact module
        module = data.get('module')
        if module not in ['Leads', 'Contacts']:
            return False, f"Unsupported module: {module}"
        
        # Check if there's data
        if 'data' not in data or not data.get('data'):
            return False, "Missing or empty data field"
        
        # All validation passed
        return True, "Valid webhook data (JSON)"
    
    def extract_lead_data(self, data):
        """
        Extract lead information from the Zoho CRM webhook data.
        
        Zoho webhooks can come in two formats:
        1. JSON format with module and data fields
        2. Form-encoded format with direct field values
        
        Args:
            data: The parsed webhook data
            
        Returns:
            dict: A dictionary containing the lead data with standardized keys
        """
        print(f"Extracting lead data from Zoho webhook: {data}")
        
        lead_data = {
            'source': LeadSource.WEBSITE,
            'custom_fields': {}
        }
        
        # Check if this is form-encoded data (direct field values)
        if 'first_name' in data or 'last_name' in data or 'email' in data or 'phone_number' in data:
            # Map form-encoded fields
            if 'first_name' in data:
                lead_data['first_name'] = data['first_name']
            
            if 'last_name' in data:
                lead_data['last_name'] = data['last_name']
            
            if 'email' in data:
                lead_data['email'] = data['email']
            
            if 'phone_number' in data:
                lead_data['phone'] = data['phone_number']
            
            if 'notes' in data:
                lead_data['notes'] = data['notes']
            
            # Add any other properties as custom fields
            standard_fields = ['first_name', 'last_name', 'email', 'phone_number', 'notes']
            for prop_name, prop_value in data.items():
                if prop_name not in standard_fields:
                    lead_data['custom_fields'][prop_name.lower()] = prop_value
            
            return lead_data
        
        # Otherwise, process as JSON format
        # Extract the first record from the data array
        records = data.get('data', [])
        if not records:
            return lead_data
        
        record = records[0]
        
        # Map standard fields based on the module
        module = data.get('module')
        
        if module == 'Leads':
            # Map Lead fields
            if 'First_Name' in record:
                lead_data['first_name'] = record['First_Name']
            
            if 'Last_Name' in record:
                lead_data['last_name'] = record['Last_Name']
            
            if 'Email' in record:
                lead_data['email'] = record['Email']
            
            if 'Phone' in record:
                lead_data['phone'] = record['Phone']
            
            if 'Description' in record:
                lead_data['notes'] = record['Description']
            
        elif module == 'Contacts':
            # Map Contact fields
            if 'First_Name' in record:
                lead_data['first_name'] = record['First_Name']
            
            if 'Last_Name' in record:
                lead_data['last_name'] = record['Last_Name']
            
            if 'Email' in record:
                lead_data['email'] = record['Email']
            
            if 'Phone' in record:
                lead_data['phone'] = record['Phone']
            
            if 'Description' in record:
                lead_data['notes'] = record['Description']
        
        # Add Zoho ID as a note
        zoho_id = record.get('id')
        if zoho_id:
            if 'notes' in lead_data:
                lead_data['notes'] += f"\nZoho {module} ID: {zoho_id}"
            else:
                lead_data['notes'] = f"Zoho {module} ID: {zoho_id}"
        
        # Add any other properties as custom fields
        standard_fields = ['First_Name', 'Last_Name', 'Email', 'Phone', 'Description', 'id']
        for prop_name, prop_value in record.items():
            if prop_name not in standard_fields:
                lead_data['custom_fields'][prop_name.lower()] = prop_value
        
        return lead_data

    def create_or_update_lead(self, lead_data, business_id):
        """
        Create a new lead based on the webhook data.
        This overrides the base method to always create a new lead
        without checking if one already exists.
        
        Args:
            lead_data: The extracted lead data
            business_id: The UUID of the business this lead belongs to
            
        Returns:
            Lead: The created Lead object
        """
        from business.models import Business
        
        # Get the business
        business = Business.objects.get(id=business_id)
        
        # Always create a new lead
        lead = Lead.objects.create(
            business=business,
            first_name=lead_data.get('first_name', ''),
            last_name=lead_data.get('last_name', ''),
            email=lead_data.get('email', ''),
            phone=lead_data.get('phone', ''),
            status=LeadStatus.NEW,
            source=lead_data.get('source', LeadSource.WEBSITE),
            notes=lead_data.get('notes', '')
        )
        
        print(f"Created new lead: {lead.id}")
        
        # Add any custom fields if they exist
        custom_fields = lead_data.get('custom_fields', {})
        if custom_fields and hasattr(business, 'industry') and business.industry:
            from ..models import LeadField
            
            for field_name, field_value in custom_fields.items():
                try:
                    # Try to find the industry field
                    industry_field = business.industry.fields.get(slug=field_name)
                    
                    # Create the lead field
                    LeadField.objects.create(
                        lead=lead,
                        field=industry_field,
                        value=field_value
                    )
                except Exception as e:
                    print(f"Could not save custom field {field_name}: {str(e)}")
        
        return lead

    def process_webhook(self, request, business_id):
        """
        Process an incoming webhook request from Zoho.
        
        This overrides the base process_webhook method to handle
        Zoho's specific webhook format.
        
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
                # Handle form-encoded data
                if request.body:
                    # Decode the URL-encoded form data
                    body_str = request.body.decode('utf-8')
                    print(f"Processing form data: {body_str}")
                    
                    # Parse the form data manually
                    form_data = {}
                    for pair in body_str.split('&'):
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            form_data[key] = unquote_plus(value)
                    
                    data = form_data
                else:
                    data = request.POST.dict()
            
            print(f"Processed webhook data: {data}")
            
            # Validate the webhook data
            is_valid, validation_message = self.validate_webhook(data, business_id)
            if not is_valid:
                print(f"Invalid webhook data from {self.name}: {validation_message}")
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
            print(f"Error processing webhook from {self.name}: {str(e)}")
            # Log the webhook error
            self.log_webhook(request, data if 'data' in locals() else {}, None, business_id, 500)
            
            # Return an error response
            return JsonResponse({
                'status': 'error',
                'message': f'Error processing webhook: {str(e)}'
            }, status=500)
