from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta, date
from .models import Booking, BookingStatus
from invoices.models import Invoice, InvoiceStatus



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
        
       
