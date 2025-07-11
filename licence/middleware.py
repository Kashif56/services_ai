from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.conf import settings

from .models import LicenceKeyUsage

class LicenceMiddleware:
    """
    Middleware to check if a user has an active license for premium features.
    
    This middleware checks if the user is accessing a premium feature and redirects
    them to the license purchase page if they don't have an active license.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Define paths that are exempt from license check
        exempt_paths = [
            # Core paths
            '/',  # Root path
            '/static/',
            '/media/',
            '/admin/',
            
            # License paths
            '/licence/',
            '/licence/purchase/',
            '/licence/success/',
            '/licence/cancel/',
            '/licence/activate/',
            '/licence/status/',
            
            # Account paths
            '/accounts/login/',
            '/accounts/logout/',
            '/accounts/signup/',
            '/accounts/verify-email/',
            '/accounts/resend-verification/',
            '/accounts/password-reset/',
            '/accounts/profile/',  # Allow profile access
            '/accounts/settings/',  # Allow settings access
            '/accounts/change-password/',  # Allow password change
        ]
        
        # Check if the user is authenticated
        if request.user.is_authenticated:
            # Skip check for exempt paths
            for path in exempt_paths:
                if request.path in path:
                    return self.get_response(request)
            
            # For all other paths, require a license
            has_licence = LicenceKeyUsage.objects.filter(user=request.user).exists()
            
            if not has_licence:
                messages.warning(request, 'This feature requires a license. Please purchase or activate a license to continue.')
                return redirect(reverse('licence:licence_home'))
        
        # Continue with the request
        return self.get_response(request)
