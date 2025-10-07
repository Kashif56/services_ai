from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Create user groups (business, staff, customer) with appropriate permissions'

    def handle(self, *args, **options):
        # Create Business Group
        business_group, created = Group.objects.get_or_create(name='business')
        if created:
            self.stdout.write(self.style.SUCCESS('Created "business" group'))
            # Business owners have full access to their business data
            # Permissions will be managed through views and middleware
        else:
            self.stdout.write(self.style.WARNING('Group "business" already exists'))

        # Create Staff Group
        staff_group, created = Group.objects.get_or_create(name='staff')
        if created:
            self.stdout.write(self.style.SUCCESS('Created "staff" group'))
            # Staff have limited access - only to their own bookings and profile
            # Add specific permissions for staff
            from bookings.models import Booking, BookingStaffAssignment
            from staff.models import StaffProfile
            
            # Get content types
            booking_ct = ContentType.objects.get_for_model(Booking)
            assignment_ct = ContentType.objects.get_for_model(BookingStaffAssignment)
            staff_profile_ct = ContentType.objects.get_for_model(StaffProfile)
            
            # Add view permissions
            permissions = [
                Permission.objects.get(codename='view_booking', content_type=booking_ct),
                Permission.objects.get(codename='view_bookingstaffassignment', content_type=assignment_ct),
                Permission.objects.get(codename='view_staffprofile', content_type=staff_profile_ct),
                Permission.objects.get(codename='change_staffprofile', content_type=staff_profile_ct),
            ]
            
            staff_group.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS('Added permissions to "staff" group'))
        else:
            self.stdout.write(self.style.WARNING('Group "staff" already exists'))

        # Create Customer Group
        customer_group, created = Group.objects.get_or_create(name='customer')
        if created:
            self.stdout.write(self.style.SUCCESS('Created "customer" group'))
            # Customers have access to their own bookings and invoices
            # Permissions will be managed through views and middleware
        else:
            self.stdout.write(self.style.WARNING('Group "customer" already exists'))

        self.stdout.write(self.style.SUCCESS('\nUser groups setup completed!'))
        self.stdout.write(self.style.SUCCESS('Groups created: business, staff, customer'))
