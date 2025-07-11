from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

from .utils import has_active_licence

def licence_required(view_func):
    """
    Decorator to check if a user has an active license.
    
    Args:
        view_func: The view function to decorate
        
    Returns:
        function: The decorated function
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if has_active_licence(request.user):
            return view_func(request, *args, **kwargs)
        else:
            messages.warning(request, 'This feature requires a license. Please purchase or activate a license to continue.')
            return redirect(reverse('licence:licence_home'))
    return _wrapped_view
