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
    print(f"Registered webhook processor for {source_id}: {processor_class.__name__}")

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
        # Print all available processors for debugging
        print(f"Available webhook processors: {list(_webhook_processors.keys())}")
        raise KeyError(f"No webhook processor registered for source: {source_id}")
    
    return _webhook_processors[source_id]()

def autodiscover_processors():
    """
    Auto-discover and register all webhook processors.
    This function looks for webhook_processor modules in the leads app.
    """
    from django.apps import apps
    
    print("Starting webhook processor autodiscovery...")
    
    # Directly register from the leads app registry
    try:
        # First, try direct import
        from ..webhook_processors import registry
        registry.register()
        print("Registered webhook processors from leads app directly")
    except (ImportError, AttributeError) as e:
        print(f"Failed to import registry directly: {str(e)}")
        
        # Try alternative import approach
        try:
            # Force import the registry module from the current package
            from . import registry
            registry.register()
            print("Registered webhook processors from leads.webhook_processors")
        except (ImportError, AttributeError) as e:
            print(f"Failed to import registry from current package: {str(e)}")
            
            # Manual registration as a fallback
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
                
                print("Manually registered webhook processors as fallback")
            except Exception as e:
                print(f"Failed to manually register processors: {str(e)}")
    
    # Print all registered processors for debugging
    print(f"Registered webhook processors after autodiscovery: {list(_webhook_processors.keys())}")
