from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta, date, datetime
from decimal import Decimal
import json
from .models import Booking, BookingStatus
from invoices.models import Invoice, InvoiceStatus

# Import for integration
from integration.views import send_booking_data_to_integration
from integration.models import PlatformIntegration


@receiver(post_save, sender=Booking)
def create_invoice_for_booking(sender, instance, created, **kwargs):
    if created:
        if isinstance(instance.booking_date, date):
            due_date = instance.booking_date + timedelta(days=7)
        else:
            due_date = timezone.now().date() + timedelta(days=7)
        
        Invoice.objects.create(
            booking=instance,
            status=InvoiceStatus.PENDING,
            due_date=due_date,
        )

        instance.status = BookingStatus.PENDING
        instance.save(update_fields=['status'])


@receiver(post_save, sender=Booking)
def send_booking_to_integrations(sender, instance, created, **kwargs):
    """
    Send booking data to active platform integrations when a new booking is created
    """
    if created:
        try:
            # Get all active integrations for the business
            integrations = PlatformIntegration.objects.filter(
                business=instance.business,
                is_active=True
            )
            print(f"integrations.count(): {integrations.count()}")
            if not integrations.exists():
                return

            # Create the same data structure as used in test_integration
            # This is a nested structure with booking data under 'booking' key
            test_data = {}
            
            # Prepare booking data
            booking_data = {}
            
            # Add booking fields without prefixing (matching test_integration)
            for field in instance._meta.get_fields():
                if hasattr(field, 'attname') and not field.is_relation:
                    field_name = field.attname
                    value = getattr(instance, field.attname, None)
                    
                    # Handle special types for proper serialization
                    if isinstance(value, Decimal):
                        booking_data[field_name] = float(value)
                    elif isinstance(value, datetime):
                        booking_data[field_name] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, date):
                        booking_data[field_name] = value.strftime('%Y-%m-%d')
                    else:
                        booking_data[field_name] = value
            
            # Add essential relationship fields (matching test_integration)
            if instance.service_offering:
                booking_data['service_offering_id'] = instance.service_offering.id
                booking_data['service_offering_name'] = instance.service_offering.name
            else:
                booking_data['service_offering_id'] = None
                booking_data['service_offering_name'] = None
                
            # Business
            if instance.business:
                booking_data['business_id'] = instance.business.id
                booking_data['business_name'] = instance.business.name
            else:
                booking_data['business_id'] = None
                booking_data['business_name'] = None
                
            # Lead
            if instance.lead:
                booking_data['lead_id'] = instance.lead.id
                booking_data['lead_name'] = instance.lead.get_full_name()
            else:
                booking_data['lead_id'] = None
                booking_data['lead_name'] = None
            
            # Add the booking data to the test_data
            test_data['booking'] = booking_data
            
            # Add service items if they exist (matching test_integration)
            from business.models import ServiceItem
            
            # Get all service items for this business
            all_service_items = ServiceItem.objects.filter(business=instance.business, is_active=True)
            
            # Get booked service items
            booked_items = {}
            if hasattr(instance, 'service_items'):
                for item in instance.service_items.all():
                    if item.service_item:
                        booked_items[item.service_item.id] = {
                            'quantity': item.quantity,
                            'price': float(item.price) if isinstance(item.price, Decimal) else item.price,
                            'selected': True
                        }
            
            # Add all service items to test_data
            for item in all_service_items:
                identifier = item.identifier or f"item_{item.id}"
                
                # If this item was booked, use the booking data
                if item.id in booked_items:
                    test_data[identifier] = {
                        'quantity': booked_items[item.id]['quantity'],
                        'price': booked_items[item.id]['price'],
                        'selected': True,
                        'name': item.name
                    }
                else:
                    # Otherwise use default values
                    test_data[identifier] = {
                        'quantity': 0,
                        'price': float(item.price_value) if isinstance(item.price_value, Decimal) else item.price_value,
                        'selected': False,
                        'name': item.name
                    }
            
            # Process each integration
            for integration in integrations:
                try:
                    # Use the existing send_booking_data_to_integration function with test_data
                    # This matches the structure used in test_integration
                    result = send_booking_data_to_integration(test_data, integration)
                    print(f"Integration result for {integration.name}: {result}")
                except Exception as e:
                    print(f"Error sending booking to integration {integration.name}: {str(e)}")
                    # Silently continue if one integration fails
                    continue
        except Exception as e:
            print(f"Error in send_booking_to_integrations: {str(e)}")
            # Don't raise exceptions that would interrupt the normal booking flow
            pass
