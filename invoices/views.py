from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Invoice,Payment



def public_invoice_detail(request, invoice_id):
    from django.conf import settings
    invoice = Invoice.objects.get(id=invoice_id)

    service_items = invoice.booking.service_items.all()
    
    services_total = 0
    if service_items.exists():
        services_total = sum(item.price_at_booking for item in service_items)
    
    total = invoice.booking.service_offering.price + services_total

    payments = Payment.objects.filter(invoice=invoice, is_refunded=False)
    # Calculate payment totals
    total_paid = sum(payment.amount for payment in payments if not payment.is_refunded)
    balance_due = total - total_paid
    
    context = {
        'invoice': invoice,
        'payments': payments,
        'service_items': service_items,
        'total_price': total,
        'total_paid': total_paid,
        'balance_due': balance_due,
        'settings': settings,
    }
    
    return render(request, 'invoices/public_invoice_detail.html', context)
