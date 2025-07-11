from .models import LicenceKeyUsage

def has_active_licence(user):
    """
    Check if a user has an active license.
    
    Args:
        user: The user to check
        
    Returns:
        bool: True if the user has an active license, False otherwise
    """
    if not user.is_authenticated:
        return False
    
    return LicenceKeyUsage.objects.filter(user=user).exists()


def get_user_licences(user):
    """
    Get all licenses for a user.
    
    Args:
        user: The user to get licenses for
        
    Returns:
        QuerySet: A queryset of LicenceKeyUsage objects for the user
    """
    if not user.is_authenticated:
        return LicenceKeyUsage.objects.none()
    
    return LicenceKeyUsage.objects.filter(user=user).select_related('licence')
