from django.db import models
from django.contrib.auth.models import User

class PluginStatus(models.TextChoices):
    """Status choices for plugins"""
    PENDING_APPROVAL = 'pending', 'Pending Approval'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    ACTIVE = 'active', 'Active'
    DISABLED = 'disabled', 'Disabled'

class Plugin(models.Model):
    """Model to store plugin information"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    version = models.CharField(max_length=20)
    author = models.CharField(max_length=100)
    email = models.EmailField()
    
    # Status and approval fields
    status = models.CharField(
        max_length=20,
        choices=PluginStatus.choices,
        default=PluginStatus.PENDING_APPROVAL,
        help_text="Current status of the plugin"
    )
    enabled = models.BooleanField(
        default=False,
        help_text="Whether the plugin is enabled (can only be true if approved)"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_plugins'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Installation metadata
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_plugins'
    )
    installed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Plugin files and configuration
    package_path = models.CharField(max_length=255)
    entry_point = models.CharField(max_length=100, default='main.py')
    plugin_class = models.CharField(max_length=100, blank=True, null=True, help_text="Name of the plugin class to instantiate")
    manifest = models.JSONField()
    
    # Security fields
    code_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="SHA256 hash of plugin code for integrity verification"
    )
    
    def __str__(self):
        return f"{self.name} ({self.version}) - {self.get_status_display()}"
    
    def can_be_loaded(self):
        """Check if plugin can be loaded and executed"""
        return self.status == PluginStatus.APPROVED and self.enabled
    
    def approve(self, user):
        """Approve the plugin"""
        from django.utils import timezone
        self.status = PluginStatus.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()
    
    def reject(self, user, reason):
        """Reject the plugin"""
        self.status = PluginStatus.REJECTED
        self.rejection_reason = reason
        self.enabled = False
        self.save()

class PluginPermission(models.Model):
    """Model to store plugin permissions"""
    plugin = models.ForeignKey(Plugin, on_delete=models.CASCADE, related_name='permissions')
    permission_name = models.CharField(max_length=100)
    enabled = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('plugin', 'permission_name')
    
    def __str__(self):
        return f"{self.plugin.name} - {self.permission_name}"

class PluginDependency(models.Model):
    """Track plugin dependencies"""
    plugin = models.ForeignKey(Plugin, on_delete=models.CASCADE, related_name='dependencies')
    package_name = models.CharField(max_length=100)
    version_spec = models.CharField(max_length=50)  # >=2.28.0, ^1.5.0, etc.
    installed_version = models.CharField(max_length=20, blank=True, null=True)
    install_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('installing', 'Installing'),
            ('installed', 'Installed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    install_error = models.TextField(blank=True, null=True)
    installed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        unique_together = ('plugin', 'package_name')
    
    def __str__(self):
        return f"{self.plugin.name} - {self.package_name} {self.version_spec}"


class PluginError(models.Model):
    """Track plugin errors"""
    plugin = models.ForeignKey(Plugin, on_delete=models.CASCADE, related_name='errors')
    error_type = models.CharField(
        max_length=50,
        choices=[
            ('import_error', 'Import Error'),
            ('runtime_error', 'Runtime Error'),
            ('permission_error', 'Permission Error'),
            ('timeout_error', 'Timeout Error'),
            ('dependency_error', 'Dependency Error'),
        ]
    )
    hook_name = models.CharField(max_length=100, blank=True, null=True)
    error_message = models.TextField()
    stack_trace = models.TextField(blank=True, null=True)
    context = models.JSONField(blank=True, null=True)
    occurred_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_plugin_errors'
    )
    
    class Meta:
        ordering = ['-occurred_at']
    
    def __str__(self):
        return f"{self.plugin.name} - {self.error_type} at {self.occurred_at}"


class PluginExecutionLog(models.Model):
    """Log plugin hook executions"""
    plugin = models.ForeignKey(Plugin, on_delete=models.CASCADE, related_name='execution_logs')
    hook_name = models.CharField(max_length=100)
    execution_time = models.FloatField(help_text="Execution time in seconds")
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)
    executed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['plugin', 'hook_name', '-executed_at']),
        ]
    
    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.plugin.name}.{self.hook_name} ({self.execution_time:.3f}s)"
