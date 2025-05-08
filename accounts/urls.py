from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication views
    path('signup/', views.signup_page, name='signup'),
    path('login/', views.login_page, name='login'),
    path('logout/', views.logout_page, name='logout'),
    
    # Password reset flow
    path('password-reset/', views.password_reset_page, name='password_reset'),
    
    # Account management
    path('profile/', views.profile_page, name='profile'),
    path('settings/', views.settings_page, name='settings'),
    path('change-password/', views.change_password_page, name='change_password'),
]
