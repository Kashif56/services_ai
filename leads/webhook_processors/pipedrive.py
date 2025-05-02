"""
Pipedrive webhook processor for handling incoming webhook requests from Pipedrive CRM.
"""
import json
import logging
from .base import WebhookProcessor
from ..models import LeadSource

logger = logging.getLogger(__name__)

class PipedriveWebhookProcessor(WebhookProcessor):
    """
    Webhook processor for Pipedrive CRM.
    Handles person (lead) creation and update events from Pipedrive.
    """
    source_id = 'pipedrive'
    name = 'Pipedrive'
    
    def validate_webhook(self, data, business_id):
        """
        Validate the webhook data from Pipedrive.
        
        Pipedrive webhooks typically include:
        - A 'meta' object with event information
        - A 'current' object with the current state of the entity
        - An 'event' field indicating the event type
        
        Args:
            data: The parsed webhook data
            business_id: The UUID of the business this webhook is for
            
        Returns:
            tuple: (is_valid, message) - A boolean indicating if the data is valid and a message
        """
        # Check if this contains the necessary fields
        if 'meta' not in data or 'current' not in data:
            return False, "Missing required fields: meta or current"
        
        # Check if this is a person event
        meta = data.get('meta', {})
        if meta.get('object') != 'person':
            return False, f"Unsupported object type: {meta.get('object')}"
        
        # Check if this is a relevant event
        event = meta.get('action')
        if event not in ['added', 'updated']:
            return False, f"Unsupported event type: {event}"
        
        # All validation passed
        return True, "Valid webhook data"
    
    def extract_lead_data(self, data):
        """
        Extract lead information from the Pipedrive webhook data.
        
        Pipedrive person webhooks contain:
        - meta: Object with event metadata
        - current: Object with the current state of the person
        
        Args:
            data: The parsed webhook data
            
        Returns:
            dict: A dictionary containing the lead data with standardized keys
        """
        lead_data = {
            'source': LeadSource.WEBSITE,
            'custom_fields': {}
        }
        
        # Extract person data
        person = data.get('current', {})
        
        # Map standard fields
        if 'first_name' in person:
            lead_data['first_name'] = person['first_name']
        
        if 'last_name' in person:
            lead_data['last_name'] = person['last_name']
        
        # Handle email (Pipedrive stores emails as an array)
        emails = person.get('email', [])
        if emails and isinstance(emails, list) and len(emails) > 0:
            primary_email = next((e.get('value') for e in emails if e.get('primary')), None)
            if primary_email:
                lead_data['email'] = primary_email
            else:
                lead_data['email'] = emails[0].get('value', '')
        
        # Handle phone (Pipedrive stores phones as an array)
        phones = person.get('phone', [])
        if phones and isinstance(phones, list) and len(phones) > 0:
            primary_phone = next((p.get('value') for p in phones if p.get('primary')), None)
            if primary_phone:
                lead_data['phone'] = primary_phone
            else:
                lead_data['phone'] = phones[0].get('value', '')
        
        # Add notes if available
        if 'notes' in person:
            lead_data['notes'] = person['notes']
        
        # Add Pipedrive ID as a note
        pipedrive_id = person.get('id')
        if pipedrive_id:
            if 'notes' in lead_data:
                lead_data['notes'] += f"\nPipedrive Person ID: {pipedrive_id}"
            else:
                lead_data['notes'] = f"Pipedrive Person ID: {pipedrive_id}"
        
        # Add any custom fields
        for field_key, field_value in person.items():
            if field_key not in ['id', 'first_name', 'last_name', 'email', 'phone', 'notes']:
                # Skip complex objects and arrays
                if not isinstance(field_value, (dict, list)):
                    lead_data['custom_fields'][field_key] = field_value
        
        return lead_data
