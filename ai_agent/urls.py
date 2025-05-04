from django.urls import path
from . import views

app_name = 'ai_agent'

urlpatterns = [
    # Unified agent dashboard
    path('', views.agent_dashboard, name='dashboard'),
    
    # Chat management
    path('chats/', views.chat_list, name='chat_list'),
    path('chats/<int:chat_id>/', views.chat_detail, name='chat_detail'),
    
    # API endpoints
    path('api/process-message/', views.process_message, name='process_message'),
    path('api/twilio-webhook/', views.twilio_webhook, name='twilio_webhook'),
    
    # Chat widget for embedding
    path('widget/<int:business_id>/', views.chat_widget, name='chat_widget'),
]
