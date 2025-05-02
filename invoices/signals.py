from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta, date
from bookings.models import Booking
from .models import Invoice

@receiver(post_save, sender=Booking)
def create_invoice_for_booking(sender, instance, created, **kwargs):
    """
    Signal handler to automatically create an invoice when a booking is created.
    """
    if created:  # Only run when a booking is first created
        # Set due date to 7 days after the booking date
        # Convert booking_date to datetime.date if it's not already
        if isinstance(instance.booking_date, date):
            due_date = instance.booking_date + timedelta(days=7)
        else:
            # Fallback in case booking_date is a string
            due_date = timezone.now().date() + timedelta(days=7)
        
        # Create the invoice
        Invoice.objects.create(
            booking=instance,
            status='pending',
            due_date=due_date,
        )
