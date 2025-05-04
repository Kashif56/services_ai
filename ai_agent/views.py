from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils import timezone
import json

from business.models import Business
from .models import Chat, Message, AgentConfig
from twilio.twiml.messaging_response import MessagingResponse
from .utils import process_sms_with_langchain, process_web_chat_with_langchain

@login_required
def agent_dashboard(request):
    """
    Unified dashboard for managing and testing AI agents for a business.
    """
    business = request.user.business
    
    # Get or create agent config
    agent_config = AgentConfig.objects.filter(business=business).first()
    if not agent_config:
        agent_config = AgentConfig.objects.create(
            business=business,
            name=f"{business.name} Assistant",
            is_active=True
        )
    
    # Get recent chats
    chats = Chat.objects.filter(business=business).order_by('-updated_at')[:10]
    
    if request.method == 'POST':
        # Handle agent config update
        agent_config.name = request.POST.get('name', agent_config.name)
        agent_config.prompt = request.POST.get('prompt', '')
        agent_config.save()
        
        return redirect('ai_agent:dashboard')
    
    context = {
        'business': business,
        'agent_config': agent_config,
        'chats': chats,
    }
    
    return render(request, 'ai_agent/ai_agent_unified.html', context)

@login_required
def chat_list(request):
    """
    List all chats for a business.
    """
    business = request.user.business
    chats = Chat.objects.filter(business=business).order_by('-updated_at')
    
    context = {
        'business': business,
        'chats': chats,
    }
    
    return render(request, 'ai_agent/chat_list.html', context)

@login_required
def chat_detail(request, chat_id):
    """
    View details of a chat including all messages.
    """
    business = request.user.business
    chat = get_object_or_404(Chat, id=chat_id, business=business)
    messages = chat.messages.all().order_by('created_at')
    
    context = {
        'business': business,
        'chat': chat,
        'messages': messages,
    }
    
    return render(request, 'ai_agent/chat_detail.html', context)

@csrf_exempt
@require_POST
def process_message(request):
    """
    API endpoint for processing messages from clients.
    This can be called from a web chat interface or SMS webhook.
    """
    try:
        print("[DEBUG] Starting process_message view")
        # Parse request body as JSON
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            print("[DEBUG] Invalid JSON in request body")
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON in request body'
            }, status=400)
        
        # Extract required fields
        business_id = data.get('business_id')
        message = data.get('message')
        phone_number = data.get('phone_number')
        session_key = data.get('session_key')
        
        print(f"[DEBUG] Received message: '{message}' for business_id: {business_id}")
        
        # Validate required fields
        if not business_id or not message or (not phone_number and not session_key):
            print("[DEBUG] Missing required fields")
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields: business_id, message, and either phone_number or session_key'
            }, status=400)
        
        # Get business
        try:
            business = Business.objects.get(id=business_id)
            print(f"[DEBUG] Found business: {business.name} (ID: {business.id})")
        except Business.DoesNotExist:
            print(f"[DEBUG] Business with ID {business_id} not found")
            return JsonResponse({
                'success': False,
                'error': f'Business with ID {business_id} not found'
            }, status=404)
        
        # Process the message using LangChain agent
        if phone_number:
            print("[DEBUG] Processing SMS message")
            response = process_sms_with_langchain(business_id, phone_number, message)
        else:
            print("[DEBUG] Processing web chat message")
            response = process_web_chat_with_langchain(business_id, session_key, message)
        
        # Get the chat ID
        chat = None
        if phone_number:
            chat = Chat.objects.filter(business_id=business_id, phone_number=phone_number).first()
        elif session_key:
            chat = Chat.objects.filter(business_id=business_id, session_key=session_key).first()
        
        print(f"[DEBUG] Chat ID: {chat.id if chat else None}")
        
        return JsonResponse({
            'success': True,
            'response': response,
            'chat_id': chat.id if chat else None
        })
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"[DEBUG] Error processing message: {str(e)}")
        print(f"[DEBUG] Traceback: {error_traceback}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_POST
def twilio_webhook(request):
    """
    Webhook for receiving SMS messages from Twilio.
    """
    try:
        # Extract message data from Twilio webhook
        from_number = request.POST.get('From')
        body = request.POST.get('Body')
        to_number = request.POST.get('To')
        
        if not from_number or not body or not to_number:
            return JsonResponse({
                'success': False,
                'error': 'Missing required Twilio parameters'
            }, status=400)
        
        # Find the business associated with this Twilio number
        try:
            # Get business by Twilio phone number from BusinessConfiguration
            business = Business.objects.filter(
                businessconfiguration__twilio_phone_number=to_number
            ).first()
            
            if not business:
                return JsonResponse({
                    'success': False,
                    'error': f'No business found for Twilio number {to_number}'
                }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error finding business: {str(e)}'
            }, status=500)
        
        # Process the message using LangChain agent
        response = process_sms_with_langchain(business.id, from_number, body)
        
        # Return TwiML response
        twiml_response = MessagingResponse()
        twiml_response.message(response)
        
        return HttpResponse(str(twiml_response), content_type='text/xml')
        
    except Exception as e:
        print(f"Error processing Twilio webhook: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_GET
def chat_widget(request, business_id):
    """
    Render the chat widget for embedding on a website.
    """
    business = get_object_or_404(Business, id=business_id)
    
    context = {
        'business': business,
    }
    
    return render(request, 'ai_agent/chat_widget.html', context)