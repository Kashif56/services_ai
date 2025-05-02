"""
Salesforce webhook processor for handling incoming webhook requests from Salesforce CRM.
"""
import json
import base64
import logging
from .base import WebhookProcessor
from ..models import LeadSource

logger = logging.getLogger(__name__)

class SalesforceWebhookProcessor(WebhookProcessor):
    """
    Webhook processor for Salesforce CRM.
    Handles lead creation and update events from Salesforce.
    """
    source_id = 'salesforce'
    name = 'Salesforce'
    
    def validate_webhook(self, data, business_id):
        """
        Validate the webhook data from Salesforce.
        
        Salesforce webhooks typically include:
        - A signature header for verification
        - A 'sobject' field with the object type
        - An 'event' field with the event type
        
        Args:
            data: The parsed webhook data
            business_id: The UUID of the business this webhook is for
            
        Returns:
            tuple: (is_valid, message) - A boolean indicating if the data is valid and a message
        """
        # Check if this is a lead or contact event
        if 'sobject' not in data:
            return False, "Missing required field: sobject"
        
        # Check if this has the necessary fields
        sobject = data.get('sobject', {})
        if 'Id' not in sobject:
            return False, "Missing required field: sobject.Id"
        
        # All validation passed
        return True, "Valid webhook data"
    
    def extract_lead_data(self, data):
        """
        Extract lead information from the Salesforce webhook data.
        
        Salesforce lead webhooks contain:
        - sobject: The lead or contact object data
        - event: The event type (created, updated, etc.)
        
        Args:
            data: The parsed webhook data
            
        Returns:
            dict: A dictionary containing the lead data with standardized keys
        """
        lead_data = {
            'source': LeadSource.WEBSITE,
            'custom_fields': {}
        }
        
        # Extract lead/contact properties
        sobject = data.get('sobject', {})
        
        # Map standard fields
        if 'FirstName' in sobject:
            lead_data['first_name'] = sobject['FirstName']
        
        if 'LastName' in sobject:
            lead_data['last_name'] = sobject['LastName']
        
        if 'Email' in sobject:
            lead_data['email'] = sobject['Email']
        
        if 'Phone' in sobject:
            lead_data['phone'] = sobject['Phone']
        
        # Add description/notes if available
        if 'Description' in sobject:
            lead_data['notes'] = sobject['Description']
        
        # Add Salesforce ID as a note
        salesforce_id = sobject.get('Id')
        if salesforce_id:
            if 'notes' in lead_data:
                lead_data['notes'] += f"\nSalesforce ID: {salesforce_id}"
            else:
                lead_data['notes'] = f"Salesforce ID: {salesforce_id}"
        
        # Add any other properties as custom fields
        for prop_name, prop_value in sobject.items():
            if prop_name not in ['FirstName', 'LastName', 'Email', 'Phone', 'Description', 'Id']:
                lead_data['custom_fields'][prop_name.lower()] = prop_value
        
        return lead_data
