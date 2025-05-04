"""
Webhook processor registry for handling incoming webhook requests from different CRM systems.
This module implements a plugin architecture for webhook processors.
"""
from django.utils.module_loading import import_string
import importlib
import sys


# Registry to store webhook processors
_webhook_processors = {}

def register_processor(source_id, processor_class):
    """
    Register a webhook processor for a specific CRM source.
    
    Args:
        source_id (str): The identifier for the CRM source (e.g., 'hubspot', 'salesforce')
        processor_class (class): The processor class to handle webhooks from this source
    """
    _webhook_processors[source_id] = processor_class
   

def get_processor(source_id):
    """
    Get the appropriate webhook processor for a given CRM source.
    
    Args:
        source_id (str): The identifier for the CRM source
        
    Returns:
        WebhookProcessor: An instance of the appropriate webhook processor
        
    Raises:
        KeyError: If no processor is registered for the given source
    """
    if source_id not in _webhook_processors:
        raise KeyError(f"No webhook processor registered for source: {source_id}")
    
    return _webhook_processors[source_id]()

def autodiscover_processors():
    """
    Auto-discover and register all webhook processors.
    This function looks for webhook_processor modules in the leads app.
    """
    from django.apps import apps
    
    
    
    # Directly register from the leads app registry
    try:
        # First, try direct import
        from ..webhook_processors import registry
        registry.register()
    
    except (ImportError, AttributeError) as e:
        
        
        try:
            # Force import the registry module from the current package
            from . import registry
            registry.register()
        
        except (ImportError, AttributeError) as e:
            
            
            try:
                # Manually register the processors
                from .zoho import ZohoWebhookProcessor
                from .hubspot import HubSpotWebhookProcessor
                from .salesforce import SalesforceWebhookProcessor
                from .pipedrive import PipedriveWebhookProcessor
                from .monday import MondayWebhookProcessor
                
                register_processor('zoho', ZohoWebhookProcessor)
                register_processor('hubspot', HubSpotWebhookProcessor)
                register_processor('salesforce', SalesforceWebhookProcessor)
                register_processor('pipedrive', PipedriveWebhookProcessor)
                register_processor('monday', MondayWebhookProcessor)
                
            
            except Exception as e:
                pass
    
    
