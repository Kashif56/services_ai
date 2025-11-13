"""
URL configuration for services_ai project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from plugins import views as plugin_views
from ai_website import views as ai_website_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ai-agent/', include('ai_agent.urls')),
    path('bookings/', include('bookings.urls')),
    path('invoices/', include('invoices.urls')),
    path('leads/', include('leads.urls')),
    path('voice-agent/', include('retell_agent.urls')),
    path('business/', include('business.urls')),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('integration/', include('integration.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('notifications/', include('notifications.urls')),
    path('plugins/', include('plugins.urls')),
    path('licence/', include('licence.urls')),
    path('staff/', include('staff.urls')),
    path('customer/', include('customer.urls')),
    path('ai-website/', include('ai_website.urls')),
    # SSE for real-time notifications - channel specified in URL path
    path('events/<channel>/', include('django_eventstream.urls')),
    # Dynamic plugin routes - catch all plugin/* URLs
    re_path(r'^plugin/(?P<plugin_slug>[\w-]+)/(?P<path>.*)$', plugin_views.plugin_route_handler),
    # Public AI-generated websites - must be last to avoid conflicts
    # Matches business slugs like 'kashif-mehmood', 'johns-plumbing', etc.
    path('sites/<slug:business_slug>/', ai_website_views.public_website, name='public_website'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
