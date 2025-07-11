from django.urls import path
from . import views

app_name = 'licence'

urlpatterns = [
    path('', views.licence_home, name='licence_home'),
    path('purchase/', views.purchase_licence, name='purchase_licence'),
    path('success/', views.payment_success, name='payment_success'),
    path('cancel/', views.payment_cancel, name='payment_cancel'),
    path('activate/', views.activate_licence, name='activate_licence'),
    path('status/', views.licence_status, name='licence_status'),
]