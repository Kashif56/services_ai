from django.contrib import admin
from .models import StaffProfile


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'staff_member', 'business', 'is_active', 'created_at']
    list_filter = ['is_active', 'business', 'created_at']
    search_fields = ['user__username', 'user__email', 'staff_member__first_name', 'staff_member__last_name', 'business__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Profile Information', {
            'fields': ('user', 'staff_member', 'business')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
