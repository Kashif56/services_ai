from django.urls import path
from . import views

app_name = 'leads'

urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.create_lead, name='create_lead'),
    path('<uuid:lead_id>/', views.lead_detail, name='lead_detail'),
    path('<uuid:lead_id>/edit/', views.edit_lead, name='edit_lead'),
    path('webhook/<uuid:business_id>/<str:lead_source>/', views.webhook_receiver, name='webhook_receiver'),
]
