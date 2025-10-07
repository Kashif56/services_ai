from django import template

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Check if user belongs to a specific group.
    Usage: {% if request.user|has_group:"staff" %}
    """
    try:
        return user.groups.filter(name=group_name).exists()
    except:
        return False
