from django.urls import path
from . import views, payment_views

app_name = 'invoices'

urlpatterns = [
  
    
    path('public/process-payment/', payment_views.public_process_payment, name='public_process_payment'),
    path('public/process-stripe-payment/', payment_views.public_process_stripe_payment, name='public_process_stripe_payment'),
    path('public/capture-stripe-payment/', payment_views.public_capture_stripe_payment, name='public_capture_stripe_payment'),
    
    # Payment processing routes (authenticated)
    path('process-payment/', payment_views.process_payment, name='process_payment'),
    path('process-stripe-payment/', payment_views.process_stripe_payment, name='process_stripe_payment'),
    path('process-manual-payment/', payment_views.process_manual_payment, name='process_manual_payment'),
    path('capture-stripe-payment/', payment_views.capture_stripe_payment, name='capture_stripe_payment'),
    path('public/<str:invoice_id>/preview/', views.public_invoice_detail, name='public_invoice_detail'),
]
