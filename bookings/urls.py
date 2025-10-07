from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.create_booking, name='create_booking'),
    path('<str:booking_id>/edit/', views.edit_booking, name='edit_booking'),
    path('<str:booking_id>/', views.booking_detail, name='booking_detail'),
    
    # API endpoints
    path('api/service-items/<str:service_id>/', views.get_service_items, name='get_service_items'),
    path('api/leads/', views.get_leads, name='get_leads'),
    path('api/check-availability/', views.check_availability, name='check_availability'),
    
    # Booking actions
    path('<str:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('<str:booking_id>/reschedule/', views.reschedule_booking, name='reschedule_booking'),
    path('<str:booking_id>/available-timeslots/', views.get_available_timeslots, name='get_available_timeslots'),
]
