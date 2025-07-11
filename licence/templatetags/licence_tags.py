from django import template
from licence.utils import has_active_licence, get_user_licences

register = template.Library()

@register.simple_tag(takes_context=True)
def user_has_licence(context):
    """
    Template tag to check if the current user has an active license.
    
    Usage:
        {% load licence_tags %}
        {% user_has_licence as has_licence %}
        {% if has_licence %}
            <!-- Show premium content -->
        {% else %}
            <!-- Show upgrade prompt -->
        {% endif %}
    
    Returns:
        bool: True if the user has an active license, False otherwise
    """
    request = context['request']
    return has_active_licence(request.user)


@register.simple_tag(takes_context=True)
def get_licences(context):
    """
    Template tag to get all licenses for the current user.
    
    Usage:
        {% load licence_tags %}
        {% get_licences as user_licences %}
        {% for licence in user_licences %}
            {{ licence.licence.key }}
        {% endfor %}
    
    Returns:
        QuerySet: A queryset of LicenceKeyUsage objects for the user
    """
    request = context['request']
    return get_user_licences(request.user)
