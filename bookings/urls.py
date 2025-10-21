from django.urls import path
from . import views, widget_views
from .views_widget_example import widget_example

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
    
    # Widget API endpoints (public, no auth required)
    path('widget/<str:business_id>/config/', widget_views.get_widget_config, name='widget_config'),
    path('widget/<str:business_id>/service-items/<str:service_id>/', widget_views.get_widget_service_items, name='widget_service_items'),
    path('widget/<str:business_id>/check-availability/', widget_views.check_widget_availability, name='widget_check_availability'),
    path('widget/<str:business_id>/create/', widget_views.create_widget_booking, name='widget_create_booking'),
    
    # Widget example page
    path('widget-example/', widget_example, name='widget_example'),
    
    # Booking actions
    path('<str:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('<str:booking_id>/reschedule/', views.reschedule_booking, name='reschedule_booking'),
    path('<str:booking_id>/available-timeslots/', views.get_available_timeslots, name='get_available_timeslots'),
    path('<str:booking_id>/trigger-event/', views.trigger_booking_event, name='trigger_booking_event'),
]
