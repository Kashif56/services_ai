"""
Plugin Error Handling System

Comprehensive error tracking, logging, and recovery.
"""

import traceback
import time
from django.utils import timezone
from plugins.models import PluginError, PluginExecutionLog, Plugin


class PluginErrorHandler:
    """Handle and log plugin errors"""
    
    # Error thresholds
    MAX_ERRORS_PER_HOUR = 10
    MAX_ERRORS_TOTAL = 50
    AUTO_DISABLE_THRESHOLD = 5  # Consecutive errors
    
    def __init__(self, plugin):
        self.plugin = plugin
    
    def log_error(self, error_type, error_message, hook_name=None, context=None):
        """Log a plugin error"""
        stack = traceback.format_exc()
        
        # Clean context to remove non-serializable objects
        clean_context = {}
        if context:
            for key, value in context.items():
                try:
                    # Try to convert to string if not JSON serializable
                    import json
                    json.dumps(value)
                    clean_context[key] = value
                except (TypeError, ValueError):
                    # If not serializable, store string representation
                    clean_context[key] = str(type(value).__name__)
        
        error = PluginError.objects.create(
            plugin=self.plugin,
            error_type=error_type,
            hook_name=hook_name,
            error_message=str(error_message),
            stack_trace=stack,
            context=clean_context
        )
        
        print(f"[ERROR] Plugin {self.plugin.name}: {error_type} - {error_message}")
        
        # Check if plugin should be auto-disabled
        self.check_auto_disable()
        
        # Send notification to admin
        self.notify_admin(error)
        
        return error
    
    def log_execution(self, hook_name, execution_time, success=True, error_message=None):
        """Log hook execution"""
        PluginExecutionLog.objects.create(
            plugin=self.plugin,
            hook_name=hook_name,
            execution_time=execution_time,
            success=success,
            error_message=error_message
        )
    
    def check_auto_disable(self):
        """Check if plugin should be auto-disabled due to errors"""
        from datetime import timedelta
        
        # Get recent errors (last hour)
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_errors = PluginError.objects.filter(
            plugin=self.plugin,
            occurred_at__gte=one_hour_ago,
            resolved=False
        ).count()
        
        # Get consecutive errors
        last_executions = PluginExecutionLog.objects.filter(
            plugin=self.plugin
        ).order_by('-executed_at')[:self.AUTO_DISABLE_THRESHOLD]
        
        consecutive_failures = len(last_executions) >= self.AUTO_DISABLE_THRESHOLD and \
                              all(not log.success for log in last_executions)
        
        # Auto-disable if thresholds exceeded
        if recent_errors >= self.MAX_ERRORS_PER_HOUR or consecutive_failures:
            self.plugin.enabled = False
            self.plugin.save()
            
            print(f"[ERROR] Auto-disabled plugin {self.plugin.name} due to excessive errors")
            
            # Notify admin
            self.notify_admin_disable()
    
    def notify_admin(self, error):
        """Send notification to admin about error"""
        try:
            from notifications.models import Notification
            from django.contrib.auth.models import User
            
            # Get superusers
            admins = User.objects.filter(is_superuser=True)
            
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    title=f"Plugin Error: {self.plugin.name}",
                    message=f"{error.error_type}: {error.error_message[:200]}",
                    notification_type="error"
                )
        except Exception as e:
            print(f"[ERROR] Failed to send admin notification: {e}")
    
    def notify_admin_disable(self):
        """Notify admin that plugin was auto-disabled"""
        try:
            from notifications.models import Notification
            from django.contrib.auth.models import User
            
            admins = User.objects.filter(is_superuser=True)
            
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    title=f"Plugin Auto-Disabled: {self.plugin.name}",
                    message=f"Plugin was automatically disabled due to excessive errors. Please review the error logs.",
                    notification_type="error"
                )
        except Exception as e:
            print(f"[ERROR] Failed to send disable notification: {e}")
    
    def get_error_stats(self):
        """Get error statistics for plugin"""
        from datetime import timedelta
        
        now = timezone.now()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        
        return {
            'total_errors': PluginError.objects.filter(plugin=self.plugin).count(),
            'unresolved_errors': PluginError.objects.filter(plugin=self.plugin, resolved=False).count(),
            'errors_last_hour': PluginError.objects.filter(
                plugin=self.plugin,
                occurred_at__gte=one_hour_ago
            ).count(),
            'errors_last_day': PluginError.objects.filter(
                plugin=self.plugin,
                occurred_at__gte=one_day_ago
            ).count(),
        }


def safe_hook_execution(plugin, hook_name, hook_callable, **kwargs):
    """Execute hook with error handling and logging"""
    error_handler = PluginErrorHandler(plugin)
    
    start_time = time.time()
    
    try:
        # Execute hook
        result = hook_callable(**kwargs)
        
        # Log success
        execution_time = time.time() - start_time
        error_handler.log_execution(hook_name, execution_time, success=True)
        
        return result
    
    except ImportError as e:
        # Import restriction violation
        execution_time = time.time() - start_time
        error_handler.log_error('import_error', str(e), hook_name, kwargs)
        error_handler.log_execution(hook_name, execution_time, success=False, error_message=str(e))
        return None
    
    except PermissionError as e:
        # Permission violation
        execution_time = time.time() - start_time
        error_handler.log_error('permission_error', str(e), hook_name, kwargs)
        error_handler.log_execution(hook_name, execution_time, success=False, error_message=str(e))
        return None
    
    except TimeoutError as e:
        # Execution timeout
        execution_time = time.time() - start_time
        error_handler.log_error('timeout_error', str(e), hook_name, kwargs)
        error_handler.log_execution(hook_name, execution_time, success=False, error_message=str(e))
        return None
    
    except Exception as e:
        # Any other error
        execution_time = time.time() - start_time
        error_handler.log_error('runtime_error', str(e), hook_name, kwargs)
        error_handler.log_execution(hook_name, execution_time, success=False, error_message=str(e))
        return None
