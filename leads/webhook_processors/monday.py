"""
Monday.com webhook processor for handling incoming webhook requests from Monday.com CRM.
"""
import json
import logging
from .base import WebhookProcessor
from ..models import LeadSource

logger = logging.getLogger(__name__)

class MondayWebhookProcessor(WebhookProcessor):
    """
    Webhook processor for Monday.com CRM.
    Handles item (lead) creation and update events from Monday.com.
    """
    source_id = 'monday'
    name = 'Monday.com'
    
    def validate_webhook(self, data, business_id):
        """
        Validate the webhook data from Monday.com.
        
        Monday.com webhooks typically include:
        - An 'event' object with event information
        - A 'pulse' or 'item' object with the item data
        
        Args:
            data: The parsed webhook data
            business_id: The UUID of the business this webhook is for
            
        Returns:
            tuple: (is_valid, message) - A boolean indicating if the data is valid and a message
        """
        # Check if this contains the necessary fields
        if 'event' not in data:
            return False, "Missing required field: event"
        
        # Check if this is a create or update event
        event = data.get('event', {})
        event_type = event.get('type')
        if event_type not in ['create_item', 'update_column_value']:
            return False, f"Unsupported event type: {event_type}"
        
        # Check if the item data is present
        if 'pulse' not in data and 'item' not in data:
            return False, "Missing required field: pulse or item"
        
        # All validation passed
        return True, "Valid webhook data"
    
    def extract_lead_data(self, data):
        """
        Extract lead information from the Monday.com webhook data.
        
        Monday.com item webhooks contain:
        - event: Object with event metadata
        - pulse/item: Object with the item data
        - column_values: Array of column values for the item
        
        Args:
            data: The parsed webhook data
            
        Returns:
            dict: A dictionary containing the lead data with standardized keys
        """
        lead_data = {
            'source': LeadSource.WEBSITE,
            'custom_fields': {}
        }
        
        # Extract item data (Monday.com uses either 'pulse' or 'item' depending on API version)
        item = data.get('pulse', data.get('item', {}))
        
        # Get column values (could be directly in the item or in a column_values field)
        column_values = item.get('column_values', [])
        
        # If column_values is a dict, convert it to a list for consistent processing
        if isinstance(column_values, dict):
            column_values = [
                {'id': k, 'title': k, 'value': v}
                for k, v in column_values.items()
            ]
        
        # Process column values based on their titles or IDs
        for column in column_values:
            column_id = column.get('id', '').lower()
            column_title = column.get('title', '').lower()
            column_value = column.get('value', '')
            
            # Try to parse JSON values
            if isinstance(column_value, str) and column_value.startswith('{'):
                try:
                    column_value = json.loads(column_value)
                    # Extract the actual value from Monday.com's JSON structure
                    if 'text' in column_value:
                        column_value = column_value['text']
                    elif 'value' in column_value:
                        column_value = column_value['value']
                except json.JSONDecodeError:
                    pass
            
            # Map to standard fields based on column title or ID
            if 'first' in column_id or 'first' in column_title:
                lead_data['first_name'] = column_value
            elif 'last' in column_id or 'last' in column_title:
                lead_data['last_name'] = column_value
            elif 'email' in column_id or 'email' in column_title:
                lead_data['email'] = column_value
            elif 'phone' in column_id or 'phone' in column_title:
                lead_data['phone'] = column_value
            elif 'note' in column_id or 'note' in column_title or 'description' in column_id or 'description' in column_title:
                lead_data['notes'] = column_value
            else:
                # Add as custom field
                field_name = column.get('title', column.get('id', f'field_{len(lead_data["custom_fields"])}'))
                lead_data['custom_fields'][field_name] = column_value
        
        # Add Monday.com ID as a note
        monday_id = item.get('id')
        if monday_id:
            if 'notes' in lead_data:
                lead_data['notes'] += f"\nMonday.com Item ID: {monday_id}"
            else:
                lead_data['notes'] = f"Monday.com Item ID: {monday_id}"
        
        # Add board info if available
        board_id = item.get('board', {}).get('id')
        if board_id:
            if 'notes' in lead_data:
                lead_data['notes'] += f"\nMonday.com Board ID: {board_id}"
            else:
                lead_data['notes'] = f"Monday.com Board ID: {board_id}"
        
        return lead_data
