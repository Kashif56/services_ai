from django.contrib import admin
from .models import (
    Booking, BookingServiceItem, StaffServiceAssignment, StaffAvailability, 
    StaffRole, StaffMember, BookingEvent, BookingEventType, ReminderType, BookingReminder
)

@admin.register(BookingEventType)
class BookingEventTypeAdmin(admin.ModelAdmin):
    list_display = ['business', 'name', 'event_key', 'icon', 'color', 'is_enabled', 'requires_reason', 'display_order']
    list_filter = ['business', 'is_enabled', 'show_in_timeline']
    search_fields = ['name', 'event_key']
    ordering = ['business', 'display_order']

@admin.register(ReminderType)
class ReminderTypeAdmin(admin.ModelAdmin):
    list_display = ['business', 'name', 'reminder_key', 'icon', 'is_enabled', 'default_hours_before', 'display_order']
    list_filter = ['business', 'is_enabled']
    search_fields = ['name', 'reminder_key']
    ordering = ['business', 'display_order']

admin.site.register(Booking)
admin.site.register(BookingServiceItem)
admin.site.register(StaffServiceAssignment)
admin.site.register(StaffAvailability)
admin.site.register(StaffRole)
admin.site.register(StaffMember)
admin.site.register(BookingEvent)
admin.site.register(BookingReminder)

