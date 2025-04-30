from django.db import models
from django.utils import timezone
import uuid
from bookings.models import Booking
from decimal import Decimal
from django.core.validators import MinValueValidator
import random

class InvoiceStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    PENDING = 'pending', 'Pending'
    PAID = 'paid', 'Paid'
    PARTIALLY_PAID = 'partially_paid', 'Partially Paid'
    OVERDUE = 'overdue', 'Overdue'
    CANCELLED = 'cancelled', 'Cancelled'
    REFUNDED = 'refunded', 'Refunded'


class PaymentMethod(models.TextChoices):
    CASH = 'cash', 'Cash'
    CREDIT_CARD = 'credit_card', 'Credit Card'
    DEBIT_CARD = 'debit_card', 'Debit Card'
    BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
    PAYPAL = 'paypal', 'PayPal'
    STRIPE = 'stripe', 'Stripe'
    OTHER = 'other', 'Other'


class Invoice(models.Model):
    """
    Main invoice model to store billing information related to bookings.
    Links to a booking and tracks payment status.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)
    due_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.booking.name}"
    
    def save(self, *args, **kwargs):
        # Generate invoice number if not set
        if not self.invoice_number:
            number = 'inv'.join(random.choices('0123456789', k=8))
            self.invoice_number = number
        
        super().save(*args, **kwargs)

    


class Payment(models.Model):
    """
    Tracks individual payments made against invoices.
    Multiple payments can be made for a single invoice.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    transaction_id = models.CharField(max_length=100, blank=True, null=True, help_text="External payment reference or transaction ID")
    payment_date = models.DateTimeField(default=timezone.now)

    is_refunded = models.BooleanField(default=False)
    refund_date = models.DateTimeField(blank=True, null=True)
    refund_transaction_id = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Payment of {self.amount} for Invoice #{self.invoice.invoice_number}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

