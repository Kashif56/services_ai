from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Industry, 
    Business, 
    IndustryField, 
    BusinessCustomField, 
    BusinessConfiguration,
    SMTPConfig,
    ServiceItem
)


class IndustryFieldInline(admin.TabularInline):
    model = IndustryField
    extra = 1
    fields = ('name', 'field_type', 'required', 'display_order', 'is_active')



@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description_short', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [IndustryFieldInline]
    
    def description_short(self, obj):
        if obj.description and len(obj.description) > 50:
            return f"{obj.description[:50]}..."
        return obj.description
    description_short.short_description = 'Description'


class BusinessCustomFieldInline(admin.TabularInline):
    model = BusinessCustomField
    extra = 0
    fields = ('name', 'field_type', 'required', 'display_order', 'is_active')


class BusinessConfigurationInline(admin.StackedInline):
    model = BusinessConfiguration
    can_delete = False
    verbose_name_plural = 'Configuration'


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', 'email', 'phone_number', 'is_active', 'created_at')
    list_filter = ('industry', 'is_active', 'created_at')
    search_fields = ('name', 'email', 'phone_number')
    readonly_fields = ('id',)
    inlines = [BusinessConfigurationInline, BusinessCustomFieldInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'industry', 'description', 'is_active', 'default_payment_method')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone_number', 'website')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'zip_code'),
            'classes': ('collapse',)
        }),
        ('Branding', {
            'fields': ('logo',),
            'classes': ('collapse',)
        }),
    )


@admin.register(IndustryField)
class IndustryFieldAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', 'field_type', 'required', 'display_order', 'is_active')
    list_filter = ('industry', 'field_type', 'required', 'is_active')
    search_fields = ('name', 'industry__name')
    list_editable = ('display_order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(BusinessCustomField)
class BusinessCustomFieldAdmin(admin.ModelAdmin):
    list_display = ('name', 'business', 'field_type', 'required', 'display_order', 'is_active')
    list_filter = ('business__industry', 'field_type', 'required', 'is_active')
    search_fields = ('name', 'business__name')
    list_editable = ('display_order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(BusinessConfiguration)
class BusinessConfigurationAdmin(admin.ModelAdmin):
    list_display = ('business', 'voice_enabled')
    list_filter = ('voice_enabled',)
    search_fields = ('business__name',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Business', {
            'fields': ('business',)
        }),
        ('Communication Settings', {
            'fields': ('voice_enabled', 'twilio_phone_number')
        }),
        ('Follow-up Configuration', {
            'fields': ('initial_response_delay',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SMTPConfig)
class SMTPConfigAdmin(admin.ModelAdmin):
    list_display = ('business', 'host', 'port', 'username', 'reply_to', 'from_email')
    list_filter = ('business',)
    search_fields = ('business__name', 'host', 'port', 'username', 'reply_to', 'from_email')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Business', {
            'fields': ('business',)
        }),
        ('SMTP Settings', {
            'fields': ('host', 'port', 'username', 'password', 'reply_to', 'from_email')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ServiceItem)
class ServiceItemAdmin(admin.ModelAdmin):
    list_display = ('business', 'name', 'identifier', 'price_value', 'is_active')
    list_filter = ('business', 'is_active')
    search_fields = ('name', 'identifier')
    list_editable = ('is_active',)
    prepopulated_fields = {'identifier': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Service Item', {
            'fields': ('business', 'name', 'identifier', 'description', 'price_type', 'price_value', 'is_active')
        }),
        ('Optional Settings', {
            'fields': ('is_optional', 'duration_minutes', 'max_quantity'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
