from django import template
from django.template.defaultfilters import stringfilter
from django.urls import reverse
import os
import importlib.util
import json
from django.http import HttpResponse
from django.shortcuts import render
from ..models import Plugin, PluginPermission
from ..plugin_manager import plugin_manager

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary using a key.
    Usage: {{ dictionary|get_item:key }}
    """
    if not dictionary:
        return None
    
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    elif isinstance(dictionary, (list, tuple)) and isinstance(key, int):
        if 0 <= key < len(dictionary):
            return dictionary[key]
    
    return None

@register.inclusion_tag('plugins/widgets/dashboard_widgets.html', takes_context=True)
def render_plugin_widgets(context):
    """
    Render all dashboard widgets from active plugins for the current user.
    Usage: {% render_plugin_widgets %}
    """
    request = context['request']
    user = request.user
    widgets_html = []
    widget_errors = []
    
    # Get all enabled plugins
    plugins = Plugin.objects.filter(enabled=True)
    
    # For each plugin, call the dashboard_widget hook
    for plugin in plugins:
        try:
            # Call the dashboard_widget hook for this plugin
            widgets = plugin_manager.call_hook('dashboard_widget',
                plugin_id=plugin.id, 
                context={
                    'request': request,
                    'user': user,
                    'plugin': plugin
                }
            )
            
            # Process the returned widgets
            if widgets:
                for widget in widgets:
                    if widget:
                        widgets_html.append(widget)
                        
        except Exception as e:
            # Log the error but continue with other plugins
            import traceback
            error_msg = f"Error rendering dashboard widget for {plugin.name}: {str(e)}"
            error_traceback = traceback.format_exc()
            print(error_msg)
            print(error_traceback)
            
            # Add error to widget_errors to display in the dashboard
            widget_errors.append({
                'plugin_name': plugin.name,
                'error_msg': error_msg,
                'traceback': error_traceback
            })
    
    return {'widgets_html': widgets_html, 'widget_errors': widget_errors}

@register.simple_tag(takes_context=True)
def plugin_inject_head(context):
    """
    Inject plugin content into page <head>
    Usage: {% plugin_inject_head %}
    """
    request = context.get('request')
    if not request:
        return ''
    
    injected_content = []
    
    # Get all enabled plugins
    plugins = Plugin.objects.filter(enabled=True)
    
    for plugin in plugins:
        try:
            results = plugin_manager.call_hook('inject_head',
                plugin_id=plugin.id,
                context={
                    'request': request,
                    'user': request.user if hasattr(request, 'user') else None
                }
            )
            
            if results:
                for content in results:
                    if content:
                        injected_content.append(content)
        except Exception as e:
            print(f"Error injecting head content for {plugin.name}: {str(e)}")
    
    return '\n'.join(injected_content)

@register.simple_tag(takes_context=True)
def plugin_inject_footer(context):
    """
    Inject plugin content into page footer
    Usage: {% plugin_inject_footer %}
    """
    request = context.get('request')
    if not request:
        return ''
    
    injected_content = []
    
    # Get all enabled plugins
    plugins = Plugin.objects.filter(enabled=True)
    
    for plugin in plugins:
        try:
            results = plugin_manager.call_hook('inject_footer',
                plugin_id=plugin.id,
                context={
                    'request': request,
                    'user': request.user if hasattr(request, 'user') else None
                }
            )
            
            if results:
                for content in results:
                    if content:
                        injected_content.append(content)
        except Exception as e:
            print(f"Error injecting footer content for {plugin.name}: {str(e)}")
    
    return '\n'.join(injected_content)

@register.filter
def plugin_has_permission(plugin, permission_name):
    """
    Check if a plugin has a specific permission enabled
    Usage: {% if plugin|plugin_has_permission:"read_leads" %}
    """
    if not plugin:
        return False
    
    return plugin.permissions.filter(
        permission_name=permission_name,
        enabled=True
    ).exists()
