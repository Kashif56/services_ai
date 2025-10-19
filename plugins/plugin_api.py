"""
Plugin API - Safe interface for plugins to interact with the application

This module provides a controlled API that plugins can use to access
application data without direct database access.
"""

from django.db.models import Q
from datetime import datetime, timedelta


class PluginAPI:
    """
    API interface provided to plugins for safe data access
    
    This class provides methods that plugins can call to interact with
    the application's data in a controlled and safe manner.
    """
    
    def __init__(self, plugin_id, context=None):
        """
        Initialize the Plugin API
        
        Args:
            plugin_id: ID of the plugin requesting access
            context: Optional context dict with request, user, etc.
        """
        self.plugin_id = plugin_id
        self.context = context or {}
        self._load_plugin()
    
    def _load_plugin(self):
        """Load the plugin model to check permissions"""
        from plugins.models import Plugin
        try:
            self.plugin = Plugin.objects.get(id=self.plugin_id)
        except Plugin.DoesNotExist:
            raise PermissionError(f"Plugin {self.plugin_id} not found")
        
        if not self.plugin.can_be_loaded():
            raise PermissionError(f"Plugin {self.plugin.name} is not approved or enabled")
    
    def _check_permission(self, permission_name):
        """Check if plugin has a specific permission enabled"""
        return self.plugin.permissions.filter(
            permission_name=permission_name,
            enabled=True
        ).exists()
    
    def _get_business(self):
        """Get the business from context"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and hasattr(request.user, 'business'):
            return request.user.business
        return None
    
    # Lead API
    def get_leads(self, filters=None, limit=100):
        """
        Get leads for the current business
        
        Args:
            filters: Optional dict of filters (status, date_range, etc.)
            limit: Maximum number of leads to return
            
        Returns:
            List of lead dictionaries
        """
        if not self._check_permission('read_leads'):
            raise PermissionError("Plugin does not have 'read_leads' permission")
        
        from leads.models import Lead
        
        business = self._get_business()
        if not business:
            return []
        
        queryset = Lead.objects.filter(business=business)
        
        # Apply filters
        if filters:
            if 'status' in filters:
                queryset = queryset.filter(status=filters['status'])
            if 'date_from' in filters:
                queryset = queryset.filter(created_at__gte=filters['date_from'])
            if 'date_to' in filters:
                queryset = queryset.filter(created_at__lte=filters['date_to'])
        
        # Limit results
        queryset = queryset[:limit]
        
        # Serialize leads
        return [self._serialize_lead(lead) for lead in queryset]
    
    def get_lead(self, lead_id):
        """Get a specific lead by ID"""
        if not self._check_permission('read_leads'):
            raise PermissionError("Plugin does not have 'read_leads' permission")
        
        from leads.models import Lead
        
        try:
            lead = Lead.objects.get(id=lead_id)
            business = self._get_business()
            
            # Ensure lead belongs to the user's business
            if business and lead.business != business:
                raise PermissionError("Access denied to this lead")
            
            return self._serialize_lead(lead)
        except Lead.DoesNotExist:
            return None
    
    def _serialize_lead(self, lead):
        """Convert lead to safe dictionary"""
        return {
            'id': lead.id,
            'first_name': lead.first_name,
            'last_name': lead.last_name,
            'email': lead.email,
            'phone': lead.phone,
            'status': lead.status,
            'created_at': lead.created_at.isoformat() if lead.created_at else None,
        }
    
    # Booking API
    def get_bookings(self, filters=None, limit=100):
        """
        Get bookings for the current business
        
        Args:
            filters: Optional dict of filters
            limit: Maximum number of bookings to return
            
        Returns:
            List of booking dictionaries
        """
        if not self._check_permission('read_bookings'):
            raise PermissionError("Plugin does not have 'read_bookings' permission")
        
        from bookings.models import Booking
        
        business = self._get_business()
        if not business:
            return []
        
        queryset = Booking.objects.filter(business=business)
        
        # Apply filters
        if filters:
            if 'status' in filters:
                queryset = queryset.filter(status=filters['status'])
            if 'date_from' in filters:
                queryset = queryset.filter(booking_date__gte=filters['date_from'])
            if 'date_to' in filters:
                queryset = queryset.filter(booking_date__lte=filters['date_to'])
        
        queryset = queryset[:limit]
        
        return [self._serialize_booking(booking) for booking in queryset]
    
    def get_booking(self, booking_id):
        """Get a specific booking by ID"""
        if not self._check_permission('read_bookings'):
            raise PermissionError("Plugin does not have 'read_bookings' permission")
        
        from bookings.models import Booking
        
        try:
            booking = Booking.objects.get(id=booking_id)
            business = self._get_business()
            
            if business and booking.business != business:
                raise PermissionError("Access denied to this booking")
            
            return self._serialize_booking(booking)
        except Booking.DoesNotExist:
            return None
    
    def _serialize_booking(self, booking):
        """Convert booking to safe dictionary"""
        return {
            'id': booking.id,
            'booking_date': booking.booking_date.isoformat() if booking.booking_date else None,
            'status': booking.status,
            'total_price': str(booking.total_price) if hasattr(booking, 'total_price') else None,
            'created_at': booking.created_at.isoformat() if booking.created_at else None,
        }
    
    # Notification API
    def send_notification(self, message, notification_type='info', user_id=None):
        """
        Send a notification to the user
        
        Args:
            message: Notification message
            notification_type: Type of notification (info, success, warning, error)
            user_id: Optional user ID to send notification to
            
        Returns:
            bool: True if notification was sent successfully
        """
        if not self._check_permission('send_notifications'):
            raise PermissionError("Plugin does not have 'send_notifications' permission")
        
        try:
            # Use django-eventstream to send SSE notification
            from django_eventstream import send_event
            
            # Get user from context if not provided
            if not user_id:
                request = self.context.get('request')
                if request and hasattr(request, 'user'):
                    user_id = request.user.id
            
            if not user_id:
                return False
            
            # Prepare event data
            event_data = {
                'type': notification_type,
                'message': message,
                'plugin': self.plugin.name,
                'timestamp': datetime.now().isoformat()
            }
            
            # Send event through SSE
            send_event(
                f'user-{user_id}',
                'message',
                event_data
            )
            
            return True
        except Exception as e:
            return False


def get_plugin_api(plugin_id, context=None):
    """
    Factory function to create a PluginAPI instance
    
    Args:
        plugin_id: ID of the plugin
        context: Optional context dict
        
    Returns:
        PluginAPI instance
    """
    return PluginAPI(plugin_id, context)
