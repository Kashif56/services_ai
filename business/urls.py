from django.urls import path
from . import views


app_name = 'business'

urlpatterns = [
    # Business registration
    path('register/', views.business_registration, name='register'),
    
    # Business profile and settings
    path('profile/', views.business_profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('pricing/', views.business_pricing, name='pricing'),
    path('booking-settings/', views.booking_settings, name='booking_settings'),
    path('notifications/', views.notification_preferences, name='notifications'),
    path('upgrade/', views.upgrade_plan, name='upgrade'),
    
    # Business configuration
    path('configuration/', views.business_configuration, name='configuration'),
    path('configuration/update/', views.update_business_configuration, name='update_configuration'),
    
    # Custom fields management
    path('custom-fields/', views.custom_fields, name='custom_fields'),
    path('custom-field/add/', views.add_custom_field, name='add_custom_field'),
    path('custom-field/update/', views.update_custom_field, name='update_custom_field'),
    path('custom-field/delete/', views.delete_custom_field, name='delete_custom_field'),
    path('custom-field/<int:field_id>/details/', views.get_custom_field_details, name='get_custom_field_details'),
    path('custom-fields/reset/', views.reset_custom_fields, name='reset_custom_fields'),
    path('custom-fields/reorder/', views.reorder_custom_fields, name='reorder_custom_fields'),
    
    # Service management
    path('service/add/', views.add_service, name='add_service'),
    path('service/update/', views.update_service, name='update_service'),
    path('service/delete/', views.delete_service, name='delete_service'),
    path('service/<uuid:service_id>/details/', views.get_service_details, name='get_service_details'),
    
    # Service item management
    path('service-item/add/', views.add_service_item, name='add_service_item'),
    path('service-item/edit/', views.edit_service_item, name='edit_service_item'),
    path('service-item/delete/', views.delete_service_item, name='delete_service_item'),
    path('api/service-items/<uuid:item_id>/', views.get_service_item_details, name='get_service_item_details'),
    # Package functionality removed
    
    # API endpoints
    path('api/industries/', views.get_industries, name='api_industries'),
    path('api/register/', views.register_business, name='api_register_business'),
]
