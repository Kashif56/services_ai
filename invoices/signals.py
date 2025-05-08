from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum, F
from decimal import Decimal
from .models import Invoice, Payment, InvoiceStatus
from bookings.models import Booking, BookingStatus, BookingServiceItem
from core.email_notifications import send_invoice_notification


@receiver(post_save, sender=Invoice)
def invoice_post_save(sender, instance, created, **kwargs):
    # Send email notification for new invoices
    if created:
        try:
            from django_q.tasks import async_task
            async_task('core.email_notifications.send_invoice_notification', instance.id)
        except ImportError:
            send_invoice_notification(instance.id)
    
    # Mark booking as confirmed if invoice is paid
    if instance.status == InvoiceStatus.PAID and instance.booking.status == BookingStatus.PENDING:
        booking = instance.booking
        booking.status = BookingStatus.CONFIRMED
        booking.save(update_fields=['status'])

