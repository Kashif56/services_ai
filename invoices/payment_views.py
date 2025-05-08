from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.decorators import login_required
import json
import uuid
import requests
from square import Square as Client
from .models import Invoice, Payment
from business.models import Business, SquareCredentials, StripeCredentials



# SQUARE PAYMENT VIEWS
@login_required
@require_http_methods(["POST"])
def process_payment(request):
    """Process a Square payment for an invoice with option to authorize only"""
    try:
        # Parse the request body
        data = json.loads(request.body)
        source_id = data.get('sourceId')
        invoice_id = data.get('invoiceId')
        auto_complete = data.get('autoComplete', True)

        # Get the invoice
        invoice = get_object_or_404(Invoice, invoiceId=invoice_id)
        business = invoice.booking.business
        square_credentials = business.square_credentials

        if not source_id:
            return JsonResponse({'success': False, 'error': 'No payment source provided'}, status=400)

        # Initialize Square client
        client = Client(
            access_token=square_credentials.access_token,
            environment='sandbox' if settings.DEBUG else 'production'
        )

        # Create unique idempotency key
        idempotency_key = f"INVOICE_{invoice.invoiceId}_{timezone.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"

        # Prepare payment body
        payment_body = {
            "source_id": source_id,
            "amount_money": {
                "amount": int(invoice.amount * 100),  # Convert to cents
                "currency": "USD"
            },
            "idempotency_key": idempotency_key,
            "note": f"Payment for invoice {invoice.invoiceId}",
            "autocomplete": auto_complete  # This controls whether payment is completed immediately
        }

        # Create the payment
        payment_api = client.payments
        result = payment_api.create_payment(body=payment_body)

        if result.is_success():
            payment_data = result.body['payment']

            # Save payment details without timezone conversion
            payment = Payment.objects.create(
                invoice=invoice,
                amount=invoice.amount,
                paymentMethod='Square',
                squarePaymentId=payment_data['id'],
                status='COMPLETED' if auto_complete else 'AUTHORIZED'
            )

            # Only mark invoice as paid if payment is completed
            if auto_complete:
                payment.paidAt = timezone.now()
                invoice.isPaid = True
                invoice.save()

            return JsonResponse({
                'success': True,
                'payment_id': payment.paymentId,
                'status': payment_data['status']
            })
        else:
            # Get error message from Square response
            error_message = "Payment processing failed"
            if result.errors:
                error = result.errors[0]
                error_message = error.get('detail', error.get('category', 'Unknown error occurred'))

            return JsonResponse({
                'success': False,
                'error': error_message
            }, status=400)

    except Exception as e:
        # Log the error for debugging
        print(f"Payment processing error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred while processing your payment. Please try again.'
        }, status=500)



@require_http_methods(["POST"])
def process_manual_payment(request):
    """Process payments (Square, Cash, Bank Transfer) for an invoice"""
    try:
        data = json.loads(request.body)
        invoice_id = data.get('invoiceId')
        payment_method = data.get('paymentMethod')
        amount = float(data.get('amount', 0))
        transaction_id = data.get('transactionId')
        square_payment_id = data.get('squarePaymentId')

        # Validate required fields
        if not all([invoice_id, payment_method, amount]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)

        # Get the invoice
        invoice = get_object_or_404(Invoice, invoiceId=invoice_id)
        business = invoice.booking.business
        square_credentials = business.square_credentials

        # Check if this is an existing Square payment with AUTHORIZED status
        if payment_method == 'Square' and square_payment_id:
            try:
                # Find the existing payment
                payment = Payment.objects.get(invoice=invoice, squarePaymentId=square_payment_id, status='AUTHORIZED')

                # Initialize Square client
                client = Client(
                    access_token=square_credentials.access_token,
                    environment='sandbox' if settings.DEBUG else 'production'
                )

                # Complete the payment in Square
                result = client.payments.complete_payment(
                    payment_id=payment.squarePaymentId,
                    body={}
                )

                if result.is_success():
                    # Update payment status
                    payment.status = 'COMPLETED'
                    payment.paidAt = timezone.now()
                    payment.save()

                    # Mark invoice as paid
                    invoice.isPaid = True
                    invoice.save()

                    return JsonResponse({
                        'success': True,
                        'message': 'Square payment completed successfully'
                    })
                else:
                    error_message = "Payment completion failed"
                    if result.errors:
                        error = result.errors[0]
                        error_message = error.get('detail', error.get('category', 'Unknown error occurred'))

                    return JsonResponse({
                        'success': False,
                        'error': error_message
                    }, status=400)
            except Payment.DoesNotExist:
                # If payment doesn't exist, continue with creating a new payment
                pass
            except Exception as e:
                print(f"Square payment completion error: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': f'Error completing Square payment: {str(e)}'
                }, status=500)

        # Create payment record
        payment = Payment.objects.create(
            invoice=invoice,
            amount=amount,
            paymentMethod=payment_method,
            transactionId=transaction_id if payment_method == 'Bank Transfer' else None,
            squarePaymentId=square_payment_id if payment_method == 'Square' else None,
            status='COMPLETED',
            paidAt=timezone.now()
        )

        # Mark invoice as paid
        invoice.isPaid = True
        invoice.save()

        return JsonResponse({
            'success': True,
            'message': f'{payment_method} payment processed successfully'
        })

    except Exception as e:
        print(f"Payment processing error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred while processing the payment.'
        }, status=500)




# STRIPE PAYMENT VIEWS
@login_required
@require_http_methods(["POST"])
def process_stripe_payment(request):
    """Process a Stripe payment for an invoice with option to authorize only"""
    try:
        # Parse the request body
        data = json.loads(request.body)
        payment_method_id = data.get('payment_method_id')
        invoice_id = data.get('invoice_id')
        amount = data.get('amount', 0)
        auto_complete = data.get('auto_complete', True)

        # Get the invoice
        invoice = get_object_or_404(Invoice, id=invoice_id)
        business = invoice.booking.business

        # Get Stripe credentials
        try:
            stripe_credentials = business.stripe_credentials
        except:
            return JsonResponse({
                'success': False,
                'error': 'Stripe credentials not found for this business'
            }, status=400)

        if not payment_method_id:
            return JsonResponse({
                'success': False,
                'error': 'No payment method provided'
            }, status=400)

        import stripe

        stripe.api_key = stripe_credentials.stripe_secret_key

        # Generate a unique idempotency key
        idempotency_key = f"invoice_{invoice.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"

        try:
            # Convert amount to cents for Stripe
            amount_in_cents = int(float(amount) * 100)

            if auto_complete:
                payment_intent = stripe.PaymentIntent.create(
                    amount=amount_in_cents,
                    currency='usd',
                    payment_method=payment_method_id,
                    confirm=True,
                    description=f"Payment for invoice {invoice.invoice_number}",
                    metadata={
                        'invoice_id': invoice.id,
                        'business_id': business.id
                    },
                    idempotency_key=idempotency_key,
                    automatic_payment_methods={
                        'enabled': True,
                        'allow_redirects': 'never'
                    }
                )

                if payment_intent.status == 'succeeded':
                    payment = Payment.objects.create(
                        invoice=invoice,
                        amount=amount,
                        payment_method='stripe',
                        transaction_id=payment_intent.id,
                        payment_date=timezone.now()
                    )

                    # Update invoice status to paid
                    invoice.status = 'paid'
                    invoice.save()

                    return JsonResponse({
                        'success': True,
                        'payment_id': payment.id,
                        'status': 'COMPLETED'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'Payment failed. Status: {payment_intent.status}'
                    }, status=400)

            else:
                # For authorization only (capture later)
                payment_intent = stripe.PaymentIntent.create(
                    amount=amount_in_cents,
                    currency='usd',
                    payment_method=payment_method_id,
                    confirmation_method='manual',
                    capture_method='manual',
                    confirm=True,
                    payment_method_types=["card"],
                    description=f"Authorization for invoice {invoice.invoice_number}",
                    metadata={
                        'invoice_id': invoice.id,
                        'business_id': business.id
                    },
                    idempotency_key=idempotency_key
                )

                if payment_intent.status in ['requires_capture', 'succeeded']:
                    # For authorized payments, we still create a Payment record
                    payment = Payment.objects.create(
                        invoice=invoice,
                        amount=amount,
                        payment_method='stripe',
                        transaction_id=payment_intent.id
                    )
                    
                    # Store the authorization status in the payment metadata
                    payment_details = {
                        'status': 'AUTHORIZED',
                        'authorization_date': timezone.now().isoformat()
                    }
                    
                    # Update the invoice with payment details
                    if not invoice.payment_details:
                        invoice.payment_details = {}
                    invoice.payment_details['stripe'] = payment_details
                    invoice.save()

                    return JsonResponse({
                        'success': True,
                        'payment_id': payment.id,
                        'status': 'AUTHORIZED'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'Authorization failed. Status: {payment_intent.status}'
                    }, status=400)

        except stripe.error.CardError as e:
            error_message = e.error.message
            return JsonResponse({
                'success': False,
                'error': error_message
            }, status=400)
        except stripe.error.StripeError as e:
            return JsonResponse({
                'success': False,
                'error': f'Stripe error: {str(e)}'
            }, status=400)

    except Exception as e:
        print(f"Stripe payment processing error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred while processing your payment. Please try again.'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def capture_stripe_payment(request):
    try:
        data = json.loads(request.body)
        payment_id = data.get('payment_id')

        # Get the payment by ID
        payment = get_object_or_404(Payment, id=payment_id)
        
        # Check if the invoice has an authorized payment
        invoice = payment.invoice
        if not invoice.payment_details or 'stripe' not in invoice.payment_details or invoice.payment_details['stripe'].get('status') != 'AUTHORIZED':
            return JsonResponse({
                'success': False,
                'error': 'No authorized payment found for this invoice'
            }, status=400)
            
        business = invoice.booking.business

        try:
            stripe_credentials = business.stripe_credentials
        except:
            return JsonResponse({
                'success': False,
                'error': 'Stripe credentials not found for this business'
            }, status=400)

        # Import Stripe
        import stripe

        # Set the Stripe API key
        stripe.api_key = stripe_credentials.stripe_secret_key

    except Exception as e:
        print(f"Stripe payment capture error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred while capturing the payment.'
        }, status=500)

# PUBLIC PAYMENT PROCESSING FUNCTIONS
# These functions are exempt from authentication requirements

@csrf_exempt
@require_http_methods(["POST"])
def public_process_payment(request):
    """Process a Square payment for an invoice with option to authorize only - public version"""
    # This is a copy of the process_payment function without the login_required decorator
    try:
        # Parse the request body
        data = json.loads(request.body)
        source_id = data.get('sourceId')
        invoice_id = data.get('invoiceId')
        auto_complete = data.get('autoComplete', True)

        # Get the invoice
        invoice = get_object_or_404(Invoice, id=invoice_id)
        business = invoice.booking.business
        
        # Rest of the function is identical to process_payment
        # Get Square credentials
        try:
            square_credentials = business.square_credentials
        except:
            return JsonResponse({
                'success': False,
                'error': 'Square credentials not found for this business'
            }, status=400)

        if not source_id:
            return JsonResponse({
                'success': False,
                'error': 'No payment source provided'
            }, status=400)

        # Initialize Square client
        client = Client(
            access_token=square_credentials.access_token,
            environment=settings.SQUARE_ENVIRONMENT
        )

        # Get the payments API client
        payments_api = client.payments

        # Calculate the amount in cents
        amount_money = {
            "amount": int(float(invoice.amount) * 100),
            "currency": "USD"
        }

        # Create a unique idempotency key
        idempotency_key = str(uuid.uuid4())

        # Create the payment request
        payment_request = {
            "source_id": source_id,
            "amount_money": amount_money,
            "idempotency_key": idempotency_key,
            "autocomplete": auto_complete,
            "note": f"Payment for invoice {invoice.invoice_number}"
        }

        # Make the payment request
        try:
            result = payments_api.create_payment(payment_request)
            payment = result.body.get('payment')

            if payment:
                # Create a Payment record
                payment_obj = Payment.objects.create(
                    invoice=invoice,
                    amount=invoice.amount,
                    payment_method='square',
                    transaction_id=payment.get('id'),
                    payment_date=timezone.now()
                )

                # Update invoice status if payment is completed
                if auto_complete:
                    invoice.status = 'paid'
                    invoice.save()
                else:
                    # For authorized payments, store the details
                    if not invoice.payment_details:
                        invoice.payment_details = {}
                    
                    invoice.payment_details['square'] = {
                        'status': 'AUTHORIZED',
                        'authorization_date': timezone.now().isoformat()
                    }
                    invoice.save()

                return JsonResponse({
                    'success': True,
                    'payment_id': payment_obj.id,
                    'status': 'COMPLETED' if auto_complete else 'AUTHORIZED'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to process payment'
                }, status=400)

        except Exception as e:
            error_message = str(e)
            return JsonResponse({
                'success': False,
                'error': error_message
            }, status=400)

    except Exception as e:
        print(f"Payment processing error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred while processing the payment.'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def public_process_stripe_payment(request):
    """Process a Stripe payment for an invoice with option to authorize only - public version"""
    # This is a copy of the process_stripe_payment function without the login_required decorator
    try:
        # Parse the request body
        data = json.loads(request.body)
        payment_method_id = data.get('payment_method_id')
        invoice_id = data.get('invoice_id')
        amount = data.get('amount', 0)
        auto_complete = data.get('auto_complete', True)

        # Get the invoice
        invoice = get_object_or_404(Invoice, id=invoice_id)
        business = invoice.booking.business

        # Get Stripe credentials
        try:
            stripe_credentials = business.stripe_credentials
        except:
            return JsonResponse({
                'success': False,
                'error': 'Stripe credentials not found for this business'
            }, status=400)

        if not payment_method_id:
            return JsonResponse({
                'success': False,
                'error': 'No payment method provided'
            }, status=400)

        import stripe

        stripe.api_key = stripe_credentials.stripe_secret_key

        # Generate a unique idempotency key
        idempotency_key = f"invoice_{invoice.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"

        try:
            # Convert amount to cents for Stripe
            amount_in_cents = int(float(amount) * 100)

            if auto_complete:
                payment_intent = stripe.PaymentIntent.create(
                    amount=amount_in_cents,
                    currency='usd',
                    payment_method=payment_method_id,
                    confirm=True,
                    description=f"Payment for invoice {invoice.invoice_number}",
                    metadata={
                        'invoice_id': invoice.id,
                        'business_id': business.id
                    },
                    idempotency_key=idempotency_key,
                    automatic_payment_methods={
                        'enabled': True,
                        'allow_redirects': 'never'
                    }
                )

                if payment_intent.status == 'succeeded':
                    payment = Payment.objects.create(
                        invoice=invoice,
                        amount=amount,
                        payment_method='stripe',
                        transaction_id=payment_intent.id,
                        payment_date=timezone.now()
                    )

                    # Update invoice status to paid
                    invoice.status = 'paid'
                    invoice.save()

                    return JsonResponse({
                        'success': True,
                        'payment_id': payment.id,
                        'status': 'COMPLETED'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'Payment failed. Status: {payment_intent.status}'
                    }, status=400)

            else:
                # For authorization only (capture later)
                payment_intent = stripe.PaymentIntent.create(
                    amount=amount_in_cents,
                    currency='usd',
                    payment_method=payment_method_id,
                    confirmation_method='manual',
                    capture_method='manual',
                    confirm=True,
                    payment_method_types=["card"],
                    description=f"Authorization for invoice {invoice.invoice_number}",
                    metadata={
                        'invoice_id': invoice.id,
                        'business_id': business.id
                    },
                    idempotency_key=idempotency_key
                )

                if payment_intent.status in ['requires_capture', 'succeeded']:
                    # For authorized payments, we still create a Payment record
                    payment = Payment.objects.create(
                        invoice=invoice,
                        amount=amount,
                        payment_method='stripe',
                        transaction_id=payment_intent.id
                    )
                    
                    # Store the authorization status in the payment metadata
                    payment_details = {
                        'status': 'AUTHORIZED',
                        'authorization_date': timezone.now().isoformat()
                    }
                    
                    # Update the invoice with payment details
                    if not invoice.payment_details:
                        invoice.payment_details = {}
                    invoice.payment_details['stripe'] = payment_details
                    invoice.save()

                    return JsonResponse({
                        'success': True,
                        'payment_id': payment.id,
                        'status': 'AUTHORIZED'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'Authorization failed. Status: {payment_intent.status}'
                    }, status=400)

        except stripe.error.CardError as e:
            error_message = e.error.message
            return JsonResponse({
                'success': False,
                'error': error_message
            }, status=400)
        except stripe.error.StripeError as e:
            return JsonResponse({
                'success': False,
                'error': f'Stripe error: {str(e)}'
            }, status=400)

    except Exception as e:
        print(f"Stripe payment processing error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred while processing your payment. Please try again.'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def public_capture_stripe_payment(request):
    """Capture a previously authorized Stripe payment - public version"""
    # This is a copy of the capture_stripe_payment function without the login_required decorator
    try:
        data = json.loads(request.body)
        payment_id = data.get('payment_id')

        # Get the payment by ID
        payment = get_object_or_404(Payment, id=payment_id)
        
        # Check if the invoice has an authorized payment
        invoice = payment.invoice
        if not invoice.payment_details or 'stripe' not in invoice.payment_details or invoice.payment_details['stripe'].get('status') != 'AUTHORIZED':
            return JsonResponse({
                'success': False,
                'error': 'No authorized payment found for this invoice'
            }, status=400)
            
        business = invoice.booking.business

        try:
            stripe_credentials = business.stripe_credentials
        except:
            return JsonResponse({
                'success': False,
                'error': 'Stripe credentials not found for this business'
            }, status=400)

        try:
            payment_intent = stripe.PaymentIntent.capture(
                payment.transaction_id,
                amount_to_capture=int(float(payment.amount) * 100)
            )

            if payment_intent.status == 'succeeded':
                # Update payment date to now
                payment.payment_date = timezone.now()
                payment.save()

                # Update invoice status to paid
                invoice.status = 'paid'
                
                # Update payment details
                if not invoice.payment_details:
                    invoice.payment_details = {}
                    
                invoice.payment_details['stripe']['status'] = 'COMPLETED'
                invoice.payment_details['stripe']['capture_date'] = timezone.now().isoformat()
                invoice.save()

                return JsonResponse({
                    'success': True,
                    'message': 'Payment captured successfully'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Payment capture failed. Status: {payment_intent.status}'
                }, status=400)

        except stripe.error.StripeError as e:
            return JsonResponse({
                'success': False,
                'error': f'Stripe error: {str(e)}'
            }, status=400)

    except Exception as e:
        print(f"Stripe payment capture error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred while capturing the payment.'
        }, status=500)

