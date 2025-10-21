"""
Chat-style views for AI Website Builder
Provides ChatGPT-like conversational interface
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import time
import json

from .models import GeneratedWebsite, WebsiteGenerationSession
from .utils import save_html_file
from .ai_service_router import generate_website, get_available_models


@login_required
def chat_builder(request):
    """
    ChatGPT-style conversational interface for website building
    """
    # Check if user has a business
    if not hasattr(request.user, 'business'):
        messages.warning(request, 'Please register your business first.')
        return redirect('business:register')
    
    # Get or create website
    try:
        website = GeneratedWebsite.objects.get(user=request.user)
        # Get conversation history
        sessions = website.generation_sessions.all().order_by('created_at')
    except GeneratedWebsite.DoesNotExist:
        website = None
        sessions = []
    
    # Get AI model preference
    try:
        ai_model = request.user.business.configuration.ai_model_preference
    except:
        ai_model = 'openai'
    
    context = {
        'website': website,
        'sessions': sessions,
        'business': request.user.business,
        'available_models': get_available_models(),
        'current_model': ai_model,

        'business_slug': website.business_slug,
    }
    
    return render(request, 'ai_website/chat_builder.html', context)


@login_required
@require_http_methods(["POST"])
def generate_website_chat(request):
    """
    AJAX endpoint to generate website with progress tracking
    Returns JSON with session ID for progress polling
    """
    try:
        data = json.loads(request.body)
        business_name = data.get('business_name', '').strip()
        user_prompt = data.get('prompt', '').strip()
        
        if not business_name or not user_prompt:
            return JsonResponse({
                'success': False,
                'error': 'Please provide both business name and prompt.'
            }, status=400)
        
        # Get user's business
        business = request.user.business
        
        # Create or get website
        website, created = GeneratedWebsite.objects.get_or_create(
            user=request.user,
            defaults={
                'business_name': business_name,
                'ai_prompt': user_prompt,
                'is_published': False,  # Don't publish until user confirms
            }
        )
        
        # If updating existing website
        if not created:
            website.business_name = business_name
            website.ai_prompt = user_prompt
            website.save()
        
        # Create generation session
        session = WebsiteGenerationSession.objects.create(
            website=website,
            user_prompt=user_prompt,
            status='pending',
            ai_response='🚀 Starting website generation...'
        )
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'message': 'Generation started'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def process_generation(request, session_id):
    """
    Process the actual website generation
    This should be called asynchronously after session is created
    """
    try:
        session = get_object_or_404(WebsiteGenerationSession, id=session_id)
        website = session.website
        
        # Check ownership
        if website.user != request.user:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        
        # Mark as processing
        session.mark_processing()
        session.update_progress(20, '🎨 Analyzing your business requirements...')
        
        start_time = time.time()
        
        try:
            # Update progress
            session.update_progress(40, '🤖 Generating website with AI...')
            
            # Check if there's existing HTML to modify
            existing_html = None
            if website.html_file_path:
                try:
                    import os
                    from django.conf import settings
                    file_path = os.path.join(settings.MEDIA_ROOT, website.html_file_path)
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            existing_html = f.read()
                        session.update_progress(35, '📄 Reading existing website for modifications...')
                except Exception as e:
                    print(f"Could not read existing HTML: {str(e)}")
                    existing_html = None
            
            # Generate HTML content using the router
            html_content, model_used = generate_website(
                website.user.business, 
                session.user_prompt,
                existing_html=existing_html
            )
            
            # Update session with model info
            if existing_html:
                session.ai_response = f'🎨 Modified using {model_used}'
            else:
                session.ai_response = f'🎨 Generated using {model_used}'
            session.save()
            
            # Update progress
            session.update_progress(70, '💾 Saving your website...')
            
            # Save HTML file
            file_path = save_html_file(website.business_slug, html_content)
            website.html_file_path = file_path
            website.save(update_fields=['html_file_path'])
            
            # Calculate generation time
            generation_time = time.time() - start_time
            
            # Mark as completed
            session.mark_completed(
                response_message=f'✅ Website generated successfully! Your website is ready at {website.get_public_url()}',
                tokens=0,  # TODO: Get actual token count from OpenAI response
                generation_time=generation_time
            )
            
            return JsonResponse({
                'success': True,
                'website_url': website.get_public_url(),
                'preview_url': '/ai-website/preview/',
                'generation_time': round(generation_time, 2)
            })
            
        except Exception as e:
            session.mark_failed(str(e))
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_session_status(request, session_id):
    """
    Get the current status of a generation session
    Used for polling progress updates
    """
    try:
        session = get_object_or_404(WebsiteGenerationSession, id=session_id)
        
        # Check ownership
        if session.website.user != request.user:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        
        return JsonResponse({
            'success': True,
            'status': session.status,
            'progress': session.progress_percentage,
            'message': session.ai_response or '',
            'error': session.error_message or '',
            'completed': session.status in ['completed', 'failed']
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_conversation_history(request):
    """
    Get the conversation history for the user's website
    """
    try:
        website = GeneratedWebsite.objects.get(user=request.user)
        sessions = website.generation_sessions.all()[:20]  # Last 20 sessions
        
        history = []
        for session in sessions:
            history.append({
                'id': session.id,
                'user_prompt': session.user_prompt,
                'ai_response': session.ai_response or '',
                'status': session.status,
                'progress': session.progress_percentage,
                'created_at': session.created_at.isoformat(),
                'completed_at': session.completed_at.isoformat() if session.completed_at else None,
            })
        
        return JsonResponse({
            'success': True,
            'history': history,
            'website_url': website.get_public_url() if website else None
        })
        
    except GeneratedWebsite.DoesNotExist:
        return JsonResponse({
            'success': True,
            'history': [],
            'website_url': None
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
