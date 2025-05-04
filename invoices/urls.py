from django.urls import path
from . import views, payment_views

app_name = 'invoices'

urlpatterns = [
    path('', views.index, name='index'),
    path('<str:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    
    # Public payment routes
    path('public/<str:invoice_id>/', payment_views.public_invoice_detail, name='public_invoice_detail'),
    path('api/payment-intent/<str:invoice_id>/', payment_views.get_payment_intent, name='get_payment_intent'),
    path('api/setup-intent/<str:invoice_id>/', payment_views.get_setup_intent, name='get_setup_intent'),
    
    # Admin payment routes
    path('api/capture-payment/<str:invoice_id>/', payment_views.capture_authorized_payment, name='capture_payment'),
]
