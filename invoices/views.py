from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import models
from django.utils import timezone

from .models import Invoice, InvoiceStatus, Payment, PaymentMethod
from bookings.models import Booking, BookingServiceItem

# Create your views here.
@login_required
def index(request):
    business = getattr(request.user, 'business', None)
    if not business:
        messages.error(request, 'Please register your business first.')
        return redirect('business:register')
    
    # Get all invoices for this business
    invoices = Invoice.objects.filter(booking__business=business).order_by('-created_at')
    
    # Get status filter if provided
    status_filter = request.GET.get('status', '')
    if status_filter and status_filter in dict(InvoiceStatus.choices):
        invoices = invoices.filter(status=status_filter)
    
    # Get date range filter if provided
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        try:
            invoices = invoices.filter(booking__booking_date__gte=date_from)
        except ValueError:
            pass
    if date_to:
        try:
            invoices = invoices.filter(booking__booking_date__lte=date_to)
        except ValueError:
            pass
    
    # Get search query if provided
    search_query = request.GET.get('search', '')
    if search_query:
        invoices = invoices.filter(
            models.Q(invoice_number__icontains=search_query) |
            models.Q(booking__name__icontains=search_query) |
            models.Q(booking__email__icontains=search_query) |
            models.Q(booking__phone_number__icontains=search_query) |
            models.Q(notes__icontains=search_query)
        )
    
    return render(request, 'invoices/index.html', {
        'title': 'Invoices',
        'invoices': invoices,
        'invoice_statuses': InvoiceStatus.choices,
        'current_status': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query
    })

@login_required
def invoice_detail(request, invoice_id):
    business = getattr(request.user, 'business', None)
    if not business:
        messages.error(request, 'Please register your business first.')
        return redirect('business:register')
    
    invoice = get_object_or_404(Invoice, id=invoice_id, booking__business=business)
    payments = Payment.objects.filter(invoice=invoice).order_by('-payment_date')
    
    # Get service items from the booking
    service_items = BookingServiceItem.objects.filter(booking=invoice.booking)
    
    # Calculate total price from service items or use base price if no items
    if service_items.exists():
        total_price = sum(item.price_at_booking * item.quantity for item in service_items)
    else:
        total_price = invoice.booking.service_offering.price if invoice.booking.service_offering else 0
    
    # Calculate payment totals
    total_paid = sum(payment.amount for payment in payments if not payment.is_refunded)
    balance_due = total_price - total_paid
    
    return render(request, 'invoices/invoice_detail.html', {
        'title': f'Invoice #{invoice.invoice_number}',
        'invoice': invoice,
        'payments': payments,
        'service_items': service_items,
        'total_price': total_price,
        'total_paid': total_paid,
        'balance_due': balance_due
    })
