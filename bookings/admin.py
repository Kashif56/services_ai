from django.contrib import admin

# Register your models here.
from .models import Booking, BookingServiceItem, ServiceOffering, ServiceOfferingItem, StaffServiceAssignment, StaffAvailability, StaffRole, StaffMember

admin.site.register(Booking)
admin.site.register(BookingServiceItem)
admin.site.register(ServiceOffering)
admin.site.register(ServiceOfferingItem)
admin.site.register(StaffServiceAssignment)
admin.site.register(StaffAvailability)
admin.site.register(StaffRole)
admin.site.register(StaffMember)
