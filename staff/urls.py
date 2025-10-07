from django.urls import path
from . import views

app_name = 'staff'

urlpatterns = [
    path('', views.staff_dashboard, name='dashboard'),
    path('bookings/', views.staff_bookings, name='bookings'),
]