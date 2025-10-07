from django.shortcuts import redirect
from django.urls import resolve, reverse
from django.contrib.auth.models import Group


class StaffAccessMiddleware:
    """
    Middleware to restrict staff users to only access allowed pages.
    Staff users can only access:
    - Core pages (landing page, etc.)
    - Auth pages (login, logout, profile, etc.)
    - Staff detail page (their own profile)
    - Static and media files
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Define allowed URL patterns for staff users
        self.allowed_namespaces = [
            'core',      # Core pages like landing page
            'accounts',  # Auth pages like login, logout, profile
            'staff',     # Staff portal pages
        ]
        
        # Define allowed URL names (without namespace)
        self.allowed_url_names = [
            'index',
            'login',
            'logout',
            'admin:index',  # Allow admin if staff has admin access
        ]
        
        # Define allowed URL names in business namespace (staff-related views)
        self.allowed_business_urls = [
            'staff',
            'staff_detail',
            'add_staff',
            'update_staff',
            'update_staff_status',
            'add_staff_availability',
            'update_staff_availability',
            'delete_staff_availability',
            'add_staff_off_day',
            'update_weekly_off_days',
            'add_service_assignment',
            'update_service_assignment',
            'delete_service_assignment',
            'add_staff_role',
            'update_staff_role',
            'delete_staff_role',
            'staff_accounts',
            'create_staff_account',
            'delete_staff_account',
            'toggle_staff_account_status',
            'reset_staff_account_password',
        ]
        
        # Define allowed URL names in bookings namespace
        self.allowed_bookings_urls = [
            'booking_detail',
        ]
        
        # Define URL path prefixes that are always allowed
        self.allowed_path_prefixes = [
            '/static/',
            '/media/',
            '/admin/jsi18n/',  # Django admin JavaScript translations
        ]
    
    def __call__(self, request):
        # Skip middleware for non-authenticated users
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Skip middleware for superusers
        if request.user.is_superuser:
            return self.get_response(request)
        
        # Check if user is in staff group
        try:
            is_staff_user = request.user.groups.filter(name='staff').exists()
        except Exception:
            is_staff_user = False
        
        # If not a staff user, allow all access
        if not is_staff_user:
            return self.get_response(request)
        
        # Staff user - check if they're accessing allowed URLs
        current_path = request.path
        
        # Check if path starts with allowed prefixes
        for prefix in self.allowed_path_prefixes:
            if current_path.startswith(prefix):
                return self.get_response(request)
        
        # Resolve the current URL
        try:
            resolved = resolve(current_path)
            url_name = resolved.url_name
            namespace = resolved.namespace
            
            # Check if namespace is allowed
            if namespace in self.allowed_namespaces:
                return self.get_response(request)
            
            # Check if URL name is allowed
            if url_name in self.allowed_url_names:
                return self.get_response(request)
            
            # Check if it's a business namespace URL that's allowed for staff
            if namespace == 'business' and url_name in self.allowed_business_urls:
                return self.get_response(request)
            
            # Check if it's a bookings namespace URL that's allowed for staff
            if namespace == 'bookings' and url_name in self.allowed_bookings_urls:
                return self.get_response(request)
            
        except Exception:
            # If URL resolution fails, redirect to staff portal
            pass
        
        # If we reach here, staff user is trying to access a restricted page
        # Redirect them to their staff detail page
        try:
            staff_profile = request.user.staff_profile
            return redirect('business:staff_detail', staff_id=staff_profile.staff_member.id)
        except Exception:
            # If staff profile doesn't exist, redirect to login
            return redirect('accounts:login')
    
    def process_exception(self, request, exception):
        """Handle exceptions during request processing"""
        return None
