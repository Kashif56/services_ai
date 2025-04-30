from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.create_booking, name='create_booking'),
    path('<uuid:booking_id>/', views.booking_detail, name='booking_detail'),
    
    # API endpoints
    path('api/service-items/<uuid:service_id>/', views.get_service_items, name='get_service_items'),
    path('api/leads/', views.get_leads, name='get_leads'),
]
