from django.contrib import admin
from .models import Plugin, PluginPermission, PluginDependency, PluginError, PluginExecutionLog

class PluginPermissionInline(admin.TabularInline):
    model = PluginPermission
    extra = 1

@admin.register(Plugin)
class PluginAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'author', 'enabled', 'installed_at')
    list_filter = ('enabled',)
    search_fields = ('name', 'description', 'author')
    readonly_fields = ('installed_at', 'updated_at')
    inlines = [PluginPermissionInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'version', 'enabled')
        }),
        ('Author Information', {
            'fields': ('author', 'email')
        }),
        ('Plugin Details', {
            'fields': ('package_path', 'entry_point', 'manifest')
        }),
        ('Timestamps', {
            'fields': ('installed_at', 'updated_at')
        }),
    )

@admin.register(PluginPermission)
class PluginPermissionAdmin(admin.ModelAdmin):
    list_display = ('plugin', 'permission_name', 'enabled')
    list_filter = ('enabled', 'plugin')
    search_fields = ('permission_name', 'plugin__name')

@admin.register(PluginDependency)
class PluginDependencyAdmin(admin.ModelAdmin):
    list_display = ('plugin', 'package_name', 'version_spec', 'install_status', 'installed_version')
    list_filter = ('install_status', 'plugin')
    search_fields = ('package_name', 'plugin__name')
    readonly_fields = ('installed_at',)


@admin.register(PluginError)
class PluginErrorAdmin(admin.ModelAdmin):
    list_display = ('plugin', 'error_type', 'hook_name', 'occurred_at', 'resolved')
    list_filter = ('error_type', 'resolved', 'plugin')
    search_fields = ('error_message', 'plugin__name', 'hook_name')
    readonly_fields = ('occurred_at', 'stack_trace')
    fieldsets = (
        (None, {
            'fields': ('plugin', 'error_type', 'hook_name', 'error_message')
        }),
        ('Details', {
            'fields': ('stack_trace', 'context', 'occurred_at')
        }),
        ('Resolution', {
            'fields': ('resolved', 'resolved_at', 'resolved_by')
        }),
    )


@admin.register(PluginExecutionLog)
class PluginExecutionLogAdmin(admin.ModelAdmin):
    list_display = ('plugin', 'hook_name', 'execution_time', 'success', 'executed_at')
    list_filter = ('success', 'plugin', 'hook_name')
    search_fields = ('plugin__name', 'hook_name')
    readonly_fields = ('executed_at',)
    date_hierarchy = 'executed_at'
