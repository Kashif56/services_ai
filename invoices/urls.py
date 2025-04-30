from django.urls import path
from . import views

app_name = 'invoices'

urlpatterns = [
    path('', views.index, name='index'),
    path('<uuid:invoice_id>/', views.invoice_detail, name='invoice_detail'),
]
