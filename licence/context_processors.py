from .utils import has_active_licence, get_user_licences

def licence_context(request):
    """
    Context processor to add license information to all templates.
    
    Args:
        request: The request object
        
    Returns:
        dict: A dictionary containing license information
    """
    context = {
        'has_active_licence': has_active_licence(request.user),
    }
    
    if request.user.is_authenticated:
        context['user_licences'] = get_user_licences(request.user)
    
    return context
