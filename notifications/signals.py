from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db.models import Q

from leads.models import Lead
from bookings.models import Booking, StaffMember, StaffAvailability
from invoices.models import Invoice
from .models import Notification

User = get_user_model()

def create_notification(user, notification_type, title, message, related_object_id=None, related_object_type=None):
    """Helper function to create notifications for multiple users"""
   
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        related_object_id=related_object_id,
        related_object_type=related_object_type
    )

@receiver(post_save, sender=Lead)
def lead_created_notification(sender, instance, created, **kwargs):
    """Create notification when a new lead is created"""
    if created:
        # Get all staff users for the business
        business = instance.business
        
        
        create_notification(
            user=business.user,
            notification_type='lead_created',
            title='New Lead Created',
            message=f'A new lead ({instance.get_full_name()}) has been created.',
            related_object_id=instance.id,
            related_object_type='lead'
        )

@receiver(post_save, sender=Booking)
def booking_notification(sender, instance, created, update_fields, **kwargs):
    """Create notification when a booking is created or status is changed"""
    business = instance.business
    
    
    if created:
        create_notification(
            user=business.user,
            notification_type='booking_created',
            title='New Booking Created',
            message=f'A new booking for {instance.name} has been created for {instance.booking_date}.',
            related_object_id=instance.id,
            related_object_type='booking'
        )
    elif update_fields and 'status' in update_fields:
        create_notification(
            user=business.user,
            notification_type='booking_status_changed',
            title='Booking Status Changed',
            message=f'The status of booking for {instance.name} has been changed to {instance.get_status_display()}.',
            related_object_id=instance.id,
            related_object_type='booking'
        )

@receiver(post_save, sender=Invoice)
def invoice_paid_notification(sender, instance, created, update_fields, **kwargs):
    """Create notification when an invoice is paid"""
    if not created and update_fields and 'status' in update_fields and instance.status == 'paid':
        business = instance.booking.business
        
        create_notification(
            user=business.user,
            notification_type='invoice_paid',
            title='Invoice Paid',
            message=f'Invoice #{instance.invoice_number} has been paid.',
            related_object_id=instance.id,
            related_object_type='invoice'
        )

@receiver(post_save, sender=StaffMember)
def staff_added_notification(sender, instance, created, **kwargs):
    """Create notification when new staff is added"""
    if created:
        business = instance.business
        
        
        create_notification(
            user=business.user,
            notification_type='staff_added',
            title='New Staff Added',
            message=f'{instance.user.get_full_name()} has been added as staff.',
            related_object_id=instance.id,
            related_object_type='staff'
        )

@receiver(post_save, sender=StaffAvailability)
def staff_availability_changed_notification(sender, instance, created, **kwargs):
    """Create notification when staff availability is changed"""
    if not created:
        business = instance.staff.business
        
        create_notification(
            user=business.user,
            notification_type='staff_availability_changed',
            title='Staff Availability Changed',
            message=f'Availability for {instance.staff.user.get_full_name()} has been updated.',
            related_object_id=instance.id,
            related_object_type='staff_availability'
        )
