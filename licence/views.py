import stripe
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .models import Licence, LicenceKeyUsage, LicencePayment

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def licence_home(request):
    """Home page for license management"""
    # Check if user has an active license
    user_licenses = LicenceKeyUsage.objects.filter(user=request.user)
    context = {
        'has_licence': user_licenses.exists(),
        'licences': user_licenses,
    }
    return render(request, 'licence/home.html', context)

@login_required
def purchase_licence(request):
    """Create a Stripe payment intent for license purchase"""
    if request.method == 'POST':
        try:
            # Get the license amount from settings
            licence_amount = int(float(settings.LICENCE_AMOUNT) * 100)  # Convert to cents for Stripe
            
            # Create a payment intent
            intent = stripe.PaymentIntent.create(
                amount=licence_amount,
                currency='usd',
                description='Services AI License',
                metadata={
                    'user_id': request.user.id,
                },
                receipt_email=request.user.email
            )
            
            return JsonResponse({
                'clientSecret': intent.client_secret
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    # For GET requests, render the purchase form
    context = {
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'licence_amount': settings.LICENCE_AMOUNT,
        'success_url': reverse('licence:payment_success'),
        'cancel_url': reverse('licence:payment_cancel'),
    }
    
    return render(request, 'licence/purchase.html', context)

@login_required
def payment_success(request):
    """Handle successful payment and create license"""
    payment_intent_id = request.GET.get('payment_intent')
    
    if not payment_intent_id:
        # If no payment_intent is provided, just show the success page
        # This is for when the user is redirected from the Stripe payment form
        return render(request, 'licence/payment_success.html')
    
    try:
        # Retrieve the payment intent to verify payment
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        # Check if payment was successful
        if payment_intent.status == 'succeeded':
            # Check if we've already processed this payment
            if LicencePayment.objects.filter(payment_id=payment_intent_id).exists():
                messages.info(request, 'This payment has already been processed.')
                return render(request, 'licence/payment_success.html')
            
            # Generate a unique license key
            licence_key = str(uuid.uuid4())
            
            # Create the license
            licence = Licence.objects.create(key=licence_key)
            
            # Create license payment record
            LicencePayment.objects.create(
                user=request.user,
                licence=licence,
                amount=float(payment_intent.amount) / 100,  # Convert from cents
                payment_id=payment_intent_id,
            )
            
            # Create license usage record
            LicenceKeyUsage.objects.create(
                licence=licence,
                user=request.user,
            )
            
            messages.success(request, 'License purchased successfully!')
            return render(request, 'licence/payment_success.html')
        else:
            messages.error(request, f'Payment was not successful. Status: {payment_intent.status}')
            return redirect('licence:licence_home')
    except Exception as e:
        messages.error(request, f'Error processing payment: {str(e)}')
        return redirect('licence:licence_home')

@login_required
def payment_cancel(request):
    """Handle cancelled payment"""
    messages.warning(request, 'Payment was cancelled')
    return render(request, 'licence/payment_cancel.html')

@login_required
def activate_licence(request):
    """Activate a license key"""
    if request.method == 'POST':
        licence_key = request.POST.get('licence_key')
        
        if not licence_key:
            messages.error(request, 'Please provide a license key')
            return redirect('licence:activate_licence')
        
        try:
            # Find the license by key
            licence = Licence.objects.get(key=licence_key)
            
            # Check if this license is already in use by this user
            if LicenceKeyUsage.objects.filter(licence=licence, user=request.user).exists():
                messages.warning(request, 'This license is already activated for your account')
                return redirect('licence:licence_status')
            
            # Create license usage record
            LicenceKeyUsage.objects.create(
                licence=licence,
                user=request.user,
            )
            
            messages.success(request, 'License activated successfully!')
            return redirect('licence:licence_status')
        
        except Licence.DoesNotExist:
            messages.error(request, 'Invalid license key')
            return redirect('licence:activate_licence')
    
    return render(request, 'licence/activate.html')

@login_required
def licence_status(request):
    """View license status"""
    # Get all licenses for the user
    user_licenses = LicenceKeyUsage.objects.filter(user=request.user).select_related('licence')
    
    context = {
        'licences': user_licenses,
    }
    
    return render(request, 'licence/status.html', context)
