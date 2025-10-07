from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy, reverse
from django.views.decorators.csrf import csrf_protect
from django.db import IntegrityError, transaction
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
import re
import json

from .models import EmailVerification
from .verification import create_verification, verify_otp, resend_otp, send_verification_email


@csrf_protect
def signup_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Form validation
        if not (username and email and password and confirm_password):
            messages.error(request, 'All fields are required.')
            return redirect('accounts:signup')
            
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('accounts:signup')
            
        # Password strength validation
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('accounts:signup')
            
      
            
        if not re.search(r'[a-z]', password):
            messages.error(request, 'Password must contain at least one lowercase letter.')
            return redirect('accounts:signup')
            
        if not re.search(r'[0-9]', password):
            messages.error(request, 'Password must contain at least one number.')
            return redirect('accounts:signup')
            
        if not re.search(r'[^A-Za-z0-9]', password):
            messages.error(request, 'Password must contain at least one special character.')
            return redirect('accounts:signup')
        
        # Create user
        try:
            with transaction.atomic():
                # Create user but set as inactive until email verification
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    is_active=False  # User is inactive until email verification
                )
                
                # Create email verification and send OTP
                verification = create_verification(user, email)
                send_verification_email(user, email, verification.otp)
            
            # Store user ID in session for verification
            request.session['verification_user_id'] = user.id
            request.session['verification_email'] = email
            request.session.save()  # Explicitly save the session
            
            messages.success(request, 'Account created! Please check your email for the verification code.')
            return redirect('accounts:verify_email')
        except IntegrityError:
            messages.error(request, 'Username or email already exists.')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
    
    return render(request, 'accounts/signup.html')


@csrf_protect
def login_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        if not (username and password):
            messages.error(request, 'Please enter both username and password.')
            return redirect('accounts:login')
        
        # First check if user exists but is inactive (might need verification)
        try:
            user_obj = User.objects.get(username=username)
            if not user_obj.is_active:
                # Check if user has pending verification
                try:
                    verification = EmailVerification.objects.filter(user=user_obj, is_verified=False).first()
                    if verification:
                        # Store user ID in session for verification
                        request.session['verification_user_id'] = user_obj.id
                        request.session['verification_email'] = verification.email
                        
                        messages.warning(request, 'Please verify your email address before logging in.')
                        return redirect('accounts:verify_email')
                except EmailVerification.DoesNotExist:
                    print("Email Verification Does not Exists")
                    pass
        except User.DoesNotExist:
            pass
        
        user = authenticate(request, username=username, password=password)
   
        
        if user is not None:
            login(request, user)
            
            # Set session expiry based on remember_me
            if not remember_me:
                # Session expires when browser closes
                request.session.set_expiry(0)
            
            # Redirect to dashboard or home page
            next_url = request.GET.get('next', '/')
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid credentials. Please try again.')
    
    return render(request, 'accounts/login.html')


@login_required
def logout_page(request):
    redirect_url = request.GET.get('next', '/')
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect(redirect_url)


@csrf_protect
def password_reset_page(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'accounts/password_reset.html')
            
        # Check if user exists
        user_exists = User.objects.filter(email=email).exists()
        
        # Always show success message even if email doesn't exist (security best practice)
        messages.success(request, 'If an account with that email exists, a password reset link has been sent.')
        
        # Only send email if user exists
        if user_exists:
            try:
                # In a real implementation, you would use Django's PasswordResetForm
                # For now, we'll just simulate the email sending
                pass
            except Exception as e:
                # Log the error but don't reveal to user
                print(f"Error sending password reset email: {str(e)}")
        
        return redirect('accounts:login')
        
    return render(request, 'accounts/password_reset.html')



"""
Account Management View Functions

These functions should be added to the accounts/views.py file.
Copy and paste these functions at the end of your existing views.py file.
"""

@login_required
@csrf_protect
def profile_page(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        
        # Validate input
        if not (first_name and last_name and email):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'accounts/profile.html', {
                'active_tab': 'profile'
            })
        
        # Check if email already exists for another user
        if User.objects.exclude(id=request.user.id).filter(email=email).exists():
            messages.error(request, 'This email is already in use by another account.')
            return render(request, 'accounts/profile.html', {
                'active_tab': 'profile'
            })
        
        # Update user and profile
        with transaction.atomic():
            # Update User model fields
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.email = email
            request.user.save()
            
        
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('accounts:profile')
    
    return render(request, 'accounts/profile.html', {
       
        'active_tab': 'profile'
    })


@login_required
@csrf_protect
def settings_page(request):
    if request.method == 'POST':
        # Get form data
        timezone = request.POST.get('timezone')
        date_format = request.POST.get('date_format')
        time_format = request.POST.get('time_format')
        language = request.POST.get('language')
        email_notifications = request.POST.get('email_notifications') == 'on'
        sms_notifications = request.POST.get('sms_notifications') == 'on'
        
       
        
        return redirect('accounts:settings')
    
    return render(request, 'accounts/settings.html', {
        'active_tab': 'settings'
    })


@csrf_protect
def verify_email(request):
    """Handle email verification with OTP"""
    # Check if we have user_id in session
    user_id = request.session.get('verification_user_id')
    email = request.session.get('verification_email')
    
    if not user_id or not email:
        messages.error(request, 'Verification session expired. Please try signing up again.')
        return redirect('accounts:signup')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found. Please try signing up again.')
        return redirect('accounts:signup')
    
    if request.method == 'POST':
        otp = request.POST.get('otp')
        
        if not otp:
            messages.error(request, 'Please enter the verification code.')
            return render(request, 'accounts/verify_email.html', {'email': email})
        
        # Verify OTP
        is_verified, message = verify_otp(user, email, otp)
        
        if is_verified:
            # Activate user account
            user.is_active = True
            user.save()
            
            # Log in the user
            login(request, user)
            
            # Clear verification session
            if 'verification_user_id' in request.session:
                del request.session['verification_user_id']
            if 'verification_email' in request.session:
                del request.session['verification_email']
            
            messages.success(request, 'Email verified successfully! You can now register your business.')
            return redirect('business:register')
        else:
            messages.error(request, message)
    
    # Get verification object for template context
    try:
        verification = EmailVerification.objects.get(user=user, email=email)
        context = {
            'email': email,
            'is_expired': verification.is_expired,
            'max_attempts_reached': verification.max_attempts_reached,
            'attempts': verification.attempts,
            'max_attempts': verification.max_attempts,
            'can_resend': verification.can_resend
        }
    except EmailVerification.DoesNotExist:
        context = {'email': email}
    
    print(context)
    return render(request, 'accounts/verify_email.html', context)

@csrf_protect
def resend_verification(request):
    """Resend verification OTP"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    # Check if we have user_id in session
    user_id = request.session.get('verification_user_id')
    email = request.session.get('verification_email')
    
    if not user_id or not email:
        return JsonResponse({'success': False, 'message': 'Verification session expired. Please try signing up again.'})
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found. Please try signing up again.'})
    
    # Resend OTP
    success, message = resend_otp(user, email)
    
    return JsonResponse({'success': success, 'message': message})

def change_password_page(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validate input
        if not (current_password and new_password and confirm_password):
            messages.error(request, 'All fields are required.')
            return render(request, 'accounts/change_password.html', {'active_tab': 'change_password'})
        
        # Check if current password is correct
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return render(request, 'accounts/change_password.html', {'active_tab': 'change_password'})
        
        # Check if new passwords match
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return render(request, 'accounts/change_password.html', {'active_tab': 'change_password'})
        
        # Password strength validation
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'accounts/change_password.html', {'active_tab': 'change_password'})
            
        if not re.search(r'[A-Z]', new_password):
            messages.error(request, 'Password must contain at least one uppercase letter.')
            return render(request, 'accounts/change_password.html', {'active_tab': 'change_password'})
            
        if not re.search(r'[a-z]', new_password):
            messages.error(request, 'Password must contain at least one lowercase letter.')
            return render(request, 'accounts/change_password.html', {'active_tab': 'change_password'})
            
        if not re.search(r'[0-9]', new_password):
            messages.error(request, 'Password must contain at least one number.')
            return render(request, 'accounts/change_password.html', {'active_tab': 'change_password'})
            
        if not re.search(r'[^A-Za-z0-9]', new_password):
            messages.error(request, 'Password must contain at least one special character.')
            return render(request, 'accounts/change_password.html', {'active_tab': 'change_password'})
        
        # Change password
        request.user.set_password(new_password)
        request.user.save()
        
        # Update session to prevent logout
        update_session_auth_hash(request, request.user)
        
        messages.success(request, 'Password changed successfully!')
        return redirect('accounts:profile')
    
    return render(request, 'accounts/change_password.html', {'active_tab': 'change_password'})
