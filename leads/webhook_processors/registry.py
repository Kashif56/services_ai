"""
Registry for webhook processors.
This module registers all available webhook processors.
"""
from . import register_processor
from .hubspot import HubSpotWebhookProcessor
from .salesforce import SalesforceWebhookProcessor
from .zoho import ZohoWebhookProcessor
from .pipedrive import PipedriveWebhookProcessor
from .monday import MondayWebhookProcessor

def register():
    """
    Register all available webhook processors.
    """
    # Register HubSpot processor
    register_processor('hubspot', HubSpotWebhookProcessor)
    
    # Register Salesforce processor
    register_processor('salesforce', SalesforceWebhookProcessor)
    
    # Register Zoho processor
    register_processor('zoho', ZohoWebhookProcessor)
    
    # Register Pipedrive processor
    register_processor('pipedrive', PipedriveWebhookProcessor)
    
    # Register Monday.com processor
    register_processor('monday', MondayWebhookProcessor)
    
    print("All webhook processors registered successfully")
