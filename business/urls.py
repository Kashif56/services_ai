from django.urls import path
from . import views
from .import staff_views


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
    
    # Booking preferences
    path('booking-preferences/', views.booking_preferences, name='booking_preferences'),
    path('event-type/<int:event_type_id>/update/', views.update_event_type, name='update_event_type'),
    path('reminder-type/<int:reminder_type_id>/update/', views.update_reminder_type, name='update_reminder_type'),
    
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
    path('service/<str:service_id>/details/', views.get_service_details, name='get_service_details'),
    
    # Service item management
    path('service-item/manage/', views.manage_service_item, name='manage_service_item'),
    path('service-item/manage/<str:item_id>/', views.manage_service_item, name='manage_service_item_edit'),
    path('service-item/add/', views.add_service_item, name='add_service_item'),
    path('service-item/edit/', views.edit_service_item, name='edit_service_item'),
    path('service-item/delete/', views.delete_service_item, name='delete_service_item'),
    path('api/service-items/<str:item_id>/', views.get_service_item_details, name='get_service_item_details'),
    # Package functionality removed
    
    # SMTP Configuration
    path('smtp-config/', views.smtp_config, name='smtp_config'),
    path('smtp-config/update/', views.update_smtp_config, name='update_smtp_config'),
    path('smtp-config/test/', views.test_smtp_config, name='test_smtp_config'),
    
    # API endpoints
    path('api/industries/', views.get_industries, name='api_industries'),
    path('api/register/', views.register_business, name='api_register_business'),
    path('api/smtp/test/', views.test_smtp_config, name='api_test_smtp'),
    
    # Payment gateway management
    path('payment-gateways/', views.payment_gateways, name='payment_gateways'),
    path('payment-gateways/stripe/', views.save_stripe_credentials, name='save_stripe_credentials'),
    path('payment-gateways/square/', views.save_square_credentials, name='save_square_credentials'),
    path('payment-gateways/set-default/', views.set_default_payment_gateway, name='set_default_payment_gateway'),
    
    # Staff management
    path('staff/', staff_views.staff_management, name='staff'),
    path('staff/add/', staff_views.add_staff, name='add_staff'),
    path('staff/<str:staff_id>/', staff_views.staff_detail, name='staff_detail'),
    path('staff/<str:staff_id>/update/', staff_views.update_staff, name='update_staff'),
    path('staff/update-status/', staff_views.update_staff_status, name='update_staff_status'),
    path('staff/<staff_id>/add-availability/', staff_views.add_staff_availability, name='add_staff_availability'),
    path('staff/<staff_id>/update-availability/', staff_views.update_staff_availability, name='update_staff_availability'),
    path('staff/delete/availability/', staff_views.delete_staff_availability, name='delete_staff_availability'),
    path('staff/<str:staff_id>/add-off-day/', staff_views.add_staff_off_day, name='add_staff_off_day'),
    path('staff/<str:staff_id>/update-weekly-off-days/', staff_views.update_weekly_off_days, name='update_weekly_off_days'),
    
    # Staff service assignment management
    path('staff/<str:staff_id>/add-service-assignment/', staff_views.add_service_assignment, name='add_service_assignment'),
    path('staff/<str:staff_id>/update-service-assignment/', staff_views.update_service_assignment, name='update_service_assignment'),
    path('staff/delete/service-assignment/', staff_views.delete_service_assignment, name='delete_service_assignment'),
    
    # Staff role management
    path('staff-role/add/', staff_views.add_staff_role, name='add_staff_role'),
    path('staff-role/update/', staff_views.update_staff_role, name='update_staff_role'),
    path('staff-role/delete/', staff_views.delete_staff_role, name='delete_staff_role'),
    
    # Staff account management
    path('staff-accounts/', staff_views.staff_accounts, name='staff_accounts'),
    path('staff-accounts/create/', staff_views.create_staff_account, name='create_staff_account'),
    path('staff-accounts/delete/', staff_views.delete_staff_account, name='delete_staff_account'),
    path('staff-accounts/toggle-status/', staff_views.toggle_staff_account_status, name='toggle_staff_account_status'),
    path('staff-accounts/reset-password/', staff_views.reset_staff_account_password, name='reset_staff_account_password'),
]
