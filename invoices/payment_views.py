import json
from decimal import Decimal

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
import stripe

from .models import Invoice, InvoiceStatus, Payment, PaymentMethod
from .payment_processors import PaymentProcessorFactory, get_invoice_balance, get_invoice_total, update_invoice_status

# Initialize Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY

def public_invoice_detail(request, invoice_id):
    """
    View for public invoice detail page
    """
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Get service items from the booking
    service_items = invoice.booking.service_items.all()
    
    # Calculate total price from service items or use base price if no items
    if service_items.exists():
        total_price = sum(item.price_at_booking * item.quantity for item in service_items)
    else:
        total_price = invoice.booking.service_offering.price if invoice.booking.service_offering else 0
    
    # Calculate payment totals
    payments = Payment.objects.filter(invoice=invoice, is_refunded=False)
    total_paid = sum(payment.amount for payment in payments)
    balance_due = total_price - total_paid
    
    context = {
        'invoice': invoice,
        'payments': payments,
        'service_items': service_items,
        'total_price': total_price,
        'total_paid': total_paid,
        'balance_due': balance_due,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    }
    
    return render(request, 'invoices/public_invoice_detail.html', context)

def get_payment_intent(request, invoice_id):
    """
    API endpoint to create a payment intent and return the client secret
    """
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Check if invoice is already paid or cancelled
    if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]:
        return JsonResponse({'error': 'This invoice has already been paid or cancelled.'}, status=400)
    
    # Get the payment processor (default to Stripe for now)
    processor_type = request.GET.get('processor', 'stripe')
    try:
        processor = PaymentProcessorFactory.get_processor(processor_type)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    
    # Handle POST request for creating payment record after successful payment
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Process the payment success
            payment = processor.process_payment_success(invoice, data)
            
            # Update invoice status
            update_invoice_status(invoice)
            
            return JsonResponse({'success': True, 'message': 'Payment record created successfully'})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    # Handle GET request for creating a payment intent
    try:
        # Get the balance due
        balance_due = get_invoice_balance(invoice)
        
        # Create a payment intent
        response = processor.create_payment_intent(invoice, balance_due)
        
        return JsonResponse(response)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_setup_intent(request, invoice_id):
    """
    API endpoint to create a setup intent and return the client secret
    """
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Check if invoice is already paid or cancelled
    if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]:
        return JsonResponse({'error': 'This invoice has already been paid or cancelled.'}, status=400)
    
    # Get the payment processor (default to Stripe for now)
    processor_type = request.GET.get('processor', 'stripe')
    try:
        processor = PaymentProcessorFactory.get_processor(processor_type)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    
    # Handle POST request for updating invoice after successful setup
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Process the setup success
            success = processor.process_setup_success(invoice, data)
            
            if success:
                return JsonResponse({'success': True, 'message': 'Invoice updated successfully'})
            else:
                return JsonResponse({'error': 'Failed to process setup intent'}, status=500)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    # Handle GET request for creating a setup intent
    try:
        # Get the balance due
        balance_due = get_invoice_balance(invoice)
        
        # Create a setup intent
        response = processor.create_setup_intent(invoice, balance_due)
        
        return JsonResponse(response)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def capture_authorized_payment(request, invoice_id):
    """
    API endpoint to capture a previously authorized payment
    """
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Check if invoice is already paid or cancelled
    if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]:
        return JsonResponse({'error': 'This invoice has already been paid or cancelled.'}, status=400)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        payment_method_id = data.get('payment_method_id')
        processor_type = data.get('processor', 'stripe')
        
        if not payment_method_id:
            return JsonResponse({'error': 'Missing payment_method_id'}, status=400)
        
        # Get the payment processor
        try:
            processor = PaymentProcessorFactory.get_processor(processor_type)
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        
        # Get the balance due
        balance_due = get_invoice_balance(invoice)
        
        # Capture the payment
        payment = processor.capture_authorized_payment(invoice, payment_method_id, balance_due)
        
        # Update invoice status
        update_invoice_status(invoice)
        
        return JsonResponse({
            'success': True, 
            'message': 'Payment captured successfully',
            'payment_id': payment.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Webhook endpoint for payment processors
@csrf_exempt
def payment_webhook(request):
    """
    Webhook endpoint for payment processors
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
    
    # Get the payment processor type from the request
    processor_type = request.GET.get('processor', 'stripe')
    
    if processor_type == 'stripe':
        return stripe_webhook(request)
    # Add more webhook handlers for other processors as needed
    # elif processor_type == 'square':
    #     return square_webhook(request)
    # elif processor_type == 'paypal':
    #     return paypal_webhook(request)
    else:
        return JsonResponse({'error': f'Unsupported payment processor: {processor_type}'}, status=400)

def stripe_webhook(request):
    """
    Handle Stripe webhook events
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    # Handle the event
    if event.type == 'payment_intent.succeeded':
        payment_intent = event.data.object
        handle_payment_success(payment_intent)
    elif event.type == 'setup_intent.succeeded':
        setup_intent = event.data.object
        handle_setup_intent_success(setup_intent)
    # Add more event handlers as needed
    
    return JsonResponse({'status': 'success'})

def handle_payment_success(payment_intent):
    """
    Handle successful payment intent
    """
    # Get the invoice from the metadata
    invoice_id = payment_intent.metadata.get('invoice_id')
    if not invoice_id:
        return
    
    try:
        invoice = Invoice.objects.get(id=invoice_id)
    except Invoice.DoesNotExist:
        return
    
    # Create a payment record if it doesn't exist
    if not Payment.objects.filter(transaction_id=payment_intent.id).exists():
        Payment.objects.create(
            invoice=invoice,
            amount=Decimal(payment_intent.amount) / 100,  # Convert from cents
            payment_method=PaymentMethod.STRIPE,
            transaction_id=payment_intent.id,
            payment_date=timezone.now()
        )
    
    # Update invoice status
    update_invoice_status(invoice)

def handle_setup_intent_success(setup_intent):
    """
    Handle successful setup intent
    """
    # Get the invoice from the metadata
    invoice_id = setup_intent.metadata.get('invoice_id')
    if not invoice_id:
        return
    
    try:
        invoice = Invoice.objects.get(id=invoice_id)
    except Invoice.DoesNotExist:
        return
    
    # Update invoice notes with payment method ID
    payment_method = setup_intent.payment_method
    if payment_method:
        invoice.notes = f"{invoice.notes or ''}\nPayment authorized via Stripe on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}. Payment method ID: {payment_method}"
        invoice.save()

def get_invoice_balance(invoice):
    """
    Helper function to calculate the balance due for an invoice
    """
    # Get service items from the booking
    service_items = invoice.booking.service_items.all()
    
    # Calculate total price from service items or use base price if no items
    if service_items.exists():
        total_price = sum(item.price_at_booking * item.quantity for item in service_items)
    else:
        total_price = invoice.booking.service_offering.price if invoice.booking.service_offering else 0
    
    # Calculate payment totals
    payments = Payment.objects.filter(invoice=invoice, is_refunded=False)
    total_paid = sum(payment.amount for payment in payments)
    balance_due = total_price - total_paid
    
    return balance_due

def update_invoice_status(invoice):
    """
    Helper function to update invoice status based on payments
    """
    balance_due = get_invoice_balance(invoice)
    
    if balance_due <= 0:
        invoice.status = InvoiceStatus.PAID
    elif balance_due < get_invoice_total(invoice):
        invoice.status = InvoiceStatus.PARTIALLY_PAID
    
    invoice.save()

def get_invoice_total(invoice):
    """
    Helper function to get the total amount for an invoice
    """
    # Get service items from the booking
    service_items = invoice.booking.service_items.all()
    
    # Calculate total price from service items or use base price if no items
    if service_items.exists():
        total_price = sum(item.price_at_booking * item.quantity for item in service_items)
    else:
        total_price = invoice.booking.service_offering.price if invoice.booking.service_offering else 0
    
    return total_price