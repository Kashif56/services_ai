"""
HubSpot webhook processor for handling incoming webhook requests from HubSpot CRM.
"""
import json
import hmac
import hashlib
import logging
from .base import WebhookProcessor
from ..models import LeadSource

logger = logging.getLogger(__name__)

class HubSpotWebhookProcessor(WebhookProcessor):
    """
    Webhook processor for HubSpot CRM.
    Handles contact creation and update events from HubSpot.
    """
    source_id = 'hubspot'
    name = 'HubSpot'
    
    def validate_webhook(self, data, business_id):
        """
        Validate the webhook data from HubSpot.
        
        HubSpot webhooks include:
        - A signature header for verification
        - An 'object' field indicating the type of object (contact, company, etc.)
        - An 'eventId' field with the event identifier
        
        Args:
            data: The parsed webhook data
            business_id: The UUID of the business this webhook is for
            
        Returns:
            tuple: (is_valid, message) - A boolean indicating if the data is valid and a message
        """
        # Check if this is a contact event
        if 'objectId' not in data or 'objectType' not in data:
            return False, "Missing required fields: objectId or objectType"
        
        # Check if this is a contact object
        if data.get('objectType') != 'CONTACT':
            return False, f"Unsupported object type: {data.get('objectType')}"
        
        # All validation passed
        return True, "Valid webhook data"
    
    def extract_lead_data(self, data):
        """
        Extract lead information from the HubSpot webhook data.
        
        HubSpot contact webhooks contain:
        - objectId: The ID of the contact
        - objectType: The type of object (CONTACT)
        - properties: The contact properties that were changed
        
        Args:
            data: The parsed webhook data
            
        Returns:
            dict: A dictionary containing the lead data with standardized keys
        """
        lead_data = {
            'source': LeadSource.WEBSITE,
            'custom_fields': {}
        }
        
        # Extract contact properties
        properties = data.get('properties', {})
        
        # Map standard fields
        if 'firstname' in properties:
            lead_data['first_name'] = properties['firstname']
        
        if 'lastname' in properties:
            lead_data['last_name'] = properties['lastname']
        
        if 'email' in properties:
            lead_data['email'] = properties['email']
        
        if 'phone' in properties:
            lead_data['phone'] = properties['phone']
        
        # Add notes if available
        if 'notes' in properties:
            lead_data['notes'] = properties['notes']
        
        # Add HubSpot contact ID as a note
        hubspot_id = data.get('objectId')
        if hubspot_id:
            if 'notes' in lead_data:
                lead_data['notes'] += f"\nHubSpot Contact ID: {hubspot_id}"
            else:
                lead_data['notes'] = f"HubSpot Contact ID: {hubspot_id}"
        
        # Add any other properties as custom fields
        for prop_name, prop_value in properties.items():
            if prop_name not in ['firstname', 'lastname', 'email', 'phone', 'notes']:
                lead_data['custom_fields'][prop_name] = prop_value
        
        return lead_data
