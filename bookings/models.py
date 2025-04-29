from django.db import models
from django.utils import timezone
import uuid
from business.models import Business, Industry, IndustryField, BusinessCustomField, ServiceOffering, ServiceItem, ServiceOfferingItem
from leads.models import Lead, LeadStatus
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class BookingStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    RESCHEDULED = 'rescheduled', 'Rescheduled'
    CANCELLED = 'cancelled', 'Cancelled'
    COMPLETED = 'completed', 'Completed'
    NO_SHOW = 'no_show', 'No Show'


# ServiceType model has been replaced by ServiceOffering in business.models


class StaffRole(models.Model):
    """
    Defines different roles for staff members in a business.
    Each business can create custom roles based on their industry needs.
    Examples: Dentist, Hygienist, Stylist, Technician, Consultant, etc.
    """
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='staff_roles')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Staff Role"
        verbose_name_plural = "Staff Roles"
        ordering = ['business', 'name']
        unique_together = ['business', 'slug']
    
    def __str__(self):
        return f"{self.business.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class StaffMember(models.Model):
    """
    Represents staff members who provide services and can be assigned to bookings.
    Each staff member belongs to a business and can have one or more roles.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='staff_members')
    roles = models.ManyToManyField(StaffRole, related_name='staff_members')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    bio = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(upload_to='staff_profiles/', blank=True, null=True)
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=1, 
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)],
        blank=True,
        null=True
    )
    is_available = models.BooleanField(default=True, help_text="Whether this staff member is generally available for bookings")
    is_active = models.BooleanField(default=True, help_text="Whether this staff member is active in the system")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Staff Member"
        verbose_name_plural = "Staff Members"
        ordering = ['business', 'first_name', 'last_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.business.name}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


class StaffServiceAssignment(models.Model):
    """
    Maps which staff members can perform which services.
    This allows for filtering available staff by service type.
    """
    staff_member = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name='service_assignments')
    service_offering = models.ForeignKey(ServiceOffering, on_delete=models.CASCADE, related_name='staff_assignments')
    is_primary = models.BooleanField(default=False, help_text="Whether this is the staff member's primary service")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Staff Service Assignment"
        verbose_name_plural = "Staff Service Assignments"
        unique_together = ['staff_member', 'service_offering']
    
    def __str__(self):
        return f"{self.staff_member.get_full_name()} - {self.service_offering.name}"


class AVAILABILITY_TYPE(models.TextChoices):
    WEEKLY = 'weekly', 'Weekly Recurring'
    SPECIFIC = 'specific', 'Specific Date'


class WEEKDAY_CHOICES(models.IntegerChoices):
    MONDAY = 0, 'Monday'
    TUESDAY = 1, 'Tuesday'
    WEDNESDAY = 2, 'Wednesday'
    THURSDAY = 3, 'Thursday'
    FRIDAY = 4, 'Friday'
    SATURDAY = 5, 'Saturday'
    SUNDAY = 6, 'Sunday'


class StaffAvailability(models.Model):
    """
    Flexible scheduling system for staff members.
    Supports both recurring weekly schedules and specific date availability.
    """
    staff_member = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name='availability')
    availability_type = models.CharField(
        max_length=10,
        choices=AVAILABILITY_TYPE.choices,
        default=AVAILABILITY_TYPE.WEEKLY
    )
    # For weekly availability
    weekday = models.IntegerField(
        choices=WEEKDAY_CHOICES.choices,
        null=True,
        blank=True,
        help_text="Day of week for recurring availability"
    )
    # For specific date availability
    specific_date = models.DateField(null=True, blank=True, help_text="Specific date for one-time availability")
    start_time = models.TimeField()
    end_time = models.TimeField()
    off_day = models.BooleanField(default=False, help_text="If true, this staff member is unavailable during this time")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Staff Availability"
        verbose_name_plural = "Staff Availabilities"
        ordering = ['staff_member', 'availability_type', 'weekday', 'specific_date', 'start_time']
    
    def __str__(self):
        if self.availability_type == AVAILABILITY_TYPE.WEEKLY:
            day = WEEKDAY_CHOICES(self.weekday).label if self.weekday is not None else "Unknown"
            availability = "Unavailable" if self.off_day else "Available"
            return f"{self.staff_member.get_full_name()} - {day} - {self.start_time} to {self.end_time} - {availability}"
        else:
            availability = "Unavailable" if self.off_day else "Available"
            return f"{self.staff_member.get_full_name()} - {self.specific_date} - {self.start_time} to {self.end_time} - {availability}"
    
    def clean(self):
        # Validate that appropriate fields are filled based on availability type
        if self.availability_type == AVAILABILITY_TYPE.WEEKLY and self.weekday is None:
            raise ValidationError("Weekday must be specified for weekly availability")
        
        if self.availability_type == AVAILABILITY_TYPE.SPECIFIC and self.specific_date is None:
            raise ValidationError("Specific date must be provided for specific date availability")
        
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time")
        
        # Prevent conflicting availability records
        if self.availability_type == AVAILABILITY_TYPE.WEEKLY:
            conflicts = StaffAvailability.objects.filter(
                staff_member=self.staff_member,
                availability_type=AVAILABILITY_TYPE.WEEKLY,
                weekday=self.weekday,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            ).exclude(pk=self.pk)
            
            if conflicts.exists():
                raise ValidationError("This availability conflicts with an existing weekly availability")
        
        elif self.availability_type == AVAILABILITY_TYPE.SPECIFIC:
            conflicts = StaffAvailability.objects.filter(
                staff_member=self.staff_member,
                availability_type=AVAILABILITY_TYPE.SPECIFIC,
                specific_date=self.specific_date,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            ).exclude(pk=self.pk)
            
            if conflicts.exists():
                raise ValidationError("This availability conflicts with an existing specific date availability")
    
    def is_available_at(self, check_date, check_start_time, check_end_time):
        """
        Check if staff member is available at the given date and time range.
        """
        if self.off_day:
            # If this is an off day record and it matches, staff is NOT available
            if self.availability_type == AVAILABILITY_TYPE.WEEKLY:
                if check_date.weekday() == self.weekday:
                    time_overlaps = (
                        check_start_time < self.end_time and 
                        check_end_time > self.start_time
                    )
                    if time_overlaps:
                        return False
            elif self.availability_type == AVAILABILITY_TYPE.SPECIFIC:
                if check_date == self.specific_date:
                    time_overlaps = (
                        check_start_time < self.end_time and 
                        check_end_time > self.start_time
                    )
                    if time_overlaps:
                        return False
            return True  # Not affected by this off day
        else:
            # For regular availability, check if time falls within available hours
            if self.availability_type == AVAILABILITY_TYPE.WEEKLY:
                if check_date.weekday() == self.weekday:
                    return (
                        check_start_time >= self.start_time and 
                        check_end_time <= self.end_time
                    )
            elif self.availability_type == AVAILABILITY_TYPE.SPECIFIC:
                if check_date == self.specific_date:
                    return (
                        check_start_time >= self.start_time and 
                        check_end_time <= self.end_time
                    )
            return False  # No matching availability


# BusinessHours and BusinessHoliday models have been replaced by the more flexible StaffAvailability model


class Booking(models.Model):
    """
    Main booking model to store appointment information.
    Links to a lead and includes all details about the scheduled appointment.
    Staff members are assigned through the BookingStaffAssignment model.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='bookings')
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='bookings', null=True, blank=True)
    service_offering = models.ForeignKey(ServiceOffering, on_delete=models.SET_NULL, null=True, related_name='bookings')
    staff_members = models.ManyToManyField(StaffMember, through='BookingStaffAssignment', related_name='assigned_bookings')
    
    # Default contact fields
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    
    status = models.CharField(max_length=20, choices=BookingStatus.choices, default=BookingStatus.PENDING)
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    location_type = models.CharField(max_length=20, choices=(
        ('onsite', 'On-site (Client Location)'),
        ('business', 'Business Location'),
        ('virtual', 'Virtual Meeting'),
    ), default='business')
    location_details = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"
        ordering = ['-start_time']
    
    def __str__(self):
        if self.lead:
            return f"{self.lead.get_full_name()} - {self.business.name} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
        return f"{self.name} - {self.business.name} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time")
        
        # Check for overlapping bookings
        overlapping = Booking.objects.filter(
            business=self.business,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
            status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.RESCHEDULED]
        ).exclude(pk=self.pk)
        
        if overlapping.exists():
            raise ValidationError("This booking overlaps with an existing booking")
    
    def save(self, *args, **kwargs):
        # Update lead status when booking is created or updated
        if self.lead and self.status == BookingStatus.CONFIRMED:
            self.lead.status = LeadStatus.APPOINTMENT_SCHEDULED
            self.lead.save(update_fields=['status', 'updated_at'])
        elif self.lead and self.status == BookingStatus.COMPLETED:
            self.lead.status = LeadStatus.APPOINTMENT_COMPLETED
            self.lead.save(update_fields=['status', 'updated_at'])
        
        super().save(*args, **kwargs)
    
    def cancel(self, reason=None):
        """
        Cancel a booking and update its status.
        """
        self.status = BookingStatus.CANCELLED
        if reason:
            self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancellation_reason', 'updated_at'])
    
    def reschedule(self, new_start_time, new_end_time):
        """
        Reschedule a booking to a new time.
        """
        self.start_time = new_start_time
        self.end_time = new_end_time
        self.status = BookingStatus.RESCHEDULED
        self.save(update_fields=['start_time', 'end_time', 'status', 'updated_at'])
    
    def mark_completed(self):
        """
        Mark a booking as completed.
        """
        self.status = BookingStatus.COMPLETED
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_no_show(self):
        """
        Mark a booking as no-show.
        """
        self.status = BookingStatus.NO_SHOW
        self.save(update_fields=['status', 'updated_at'])
    
    def get_available_staff(self):
        """
        Find available staff members for this booking based on service offering and availability.
        """
        if not self.service_offering:
            return []
        
        # Get staff members who can perform this service
        qualified_staff = StaffMember.objects.filter(
            business=self.business,
            is_active=True,
            is_available=True,
            service_assignments__service_offering=self.service_offering
        ).distinct()
        
        # Filter by availability for the booking time
        available_staff = []
        booking_date = self.start_time.date()
        booking_start_time = self.start_time.time()
        booking_end_time = self.end_time.time()
        
        for staff in qualified_staff:
            # Check if staff has any conflicting bookings
            conflicting_bookings = BookingStaffAssignment.objects.filter(
                staff_member=staff,
                booking__start_time__lt=self.end_time,
                booking__end_time__gt=self.start_time,
                booking__status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.RESCHEDULED]
            ).exclude(booking=self)
            
            if conflicting_bookings.exists():
                continue
            
            # Check staff availability
            is_available = True
            
            # First check specific date availability/unavailability
            specific_availabilities = staff.availability.filter(
                availability_type=AVAILABILITY_TYPE.SPECIFIC,
                specific_date=booking_date
            )
            
            if specific_availabilities.exists():
                # Specific date rules override weekly rules
                for avail in specific_availabilities:
                    if not avail.is_available_at(booking_date, booking_start_time, booking_end_time):
                        is_available = False
                        break
            else:
                # Check weekly availability if no specific date rules exist
                weekday = booking_date.weekday()
                weekly_availabilities = staff.availability.filter(
                    availability_type=AVAILABILITY_TYPE.WEEKLY,
                    weekday=weekday
                )
                
                if weekly_availabilities.exists():
                    # Staff has weekly availability rules for this day
                    is_available = False  # Default to unavailable unless a rule explicitly allows
                    for avail in weekly_availabilities:
                        if avail.is_available_at(booking_date, booking_start_time, booking_end_time):
                            is_available = True
                            break
                else:
                    # No availability rules for this day, default to unavailable
                    is_available = False
            
            if is_available:
                available_staff.append(staff)
        
        return available_staff


class BookingStaffAssignment(models.Model):
    """
    Associates staff members with bookings.
    Allows multiple staff members to be assigned to a booking.
    """
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='staff_assignments')
    staff_member = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name='booking_assignments')
    is_primary = models.BooleanField(default=False, help_text="Whether this staff member is the primary provider for this booking")
    assignment_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Booking Staff Assignment"
        verbose_name_plural = "Booking Staff Assignments"
        unique_together = ['booking', 'staff_member']
        ordering = ['booking', '-is_primary', 'staff_member']
    
    def __str__(self):
        primary = " (Primary)" if self.is_primary else ""
        return f"{self.booking} - {self.staff_member.get_full_name()}{primary}"
    
    def clean(self):
        # Ensure only one primary staff member per booking
        if self.is_primary:
            existing_primary = BookingStaffAssignment.objects.filter(
                booking=self.booking,
                is_primary=True
            ).exclude(pk=self.pk).first()
            
            if existing_primary:
                raise ValidationError("This booking already has a primary staff member assigned")
        
        # Check if staff member is available for this booking time
        booking_date = self.booking.start_time.date()
        booking_start_time = self.booking.start_time.time()
        booking_end_time = self.booking.end_time.time()
        
        # Check for conflicting bookings
        conflicting_bookings = BookingStaffAssignment.objects.filter(
            staff_member=self.staff_member,
            booking__start_time__lt=self.booking.end_time,
            booking__end_time__gt=self.booking.start_time,
            booking__status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.RESCHEDULED]
        ).exclude(booking=self.booking)
        
        if conflicting_bookings.exists():
            raise ValidationError("Staff member has a conflicting booking during this time")
        
        # Check staff availability
        is_available = True
        
        # First check specific date availability/unavailability
        specific_availabilities = self.staff_member.availability.filter(
            availability_type=AVAILABILITY_TYPE.SPECIFIC,
            specific_date=booking_date
        )
        
        if specific_availabilities.exists():
            # Specific date rules override weekly rules
            for avail in specific_availabilities:
                if not avail.is_available_at(booking_date, booking_start_time, booking_end_time):
                    is_available = False
                    break
        else:
            # Check weekly availability if no specific date rules exist
            weekday = booking_date.weekday()
            weekly_availabilities = self.staff_member.availability.filter(
                availability_type=AVAILABILITY_TYPE.WEEKLY,
                weekday=weekday
            )
            
            if weekly_availabilities.exists():
                # Staff has weekly availability rules for this day
                is_available = False  # Default to unavailable unless a rule explicitly allows
                for avail in weekly_availabilities:
                    if avail.is_available_at(booking_date, booking_start_time, booking_end_time):
                        is_available = True
                        break
            else:
                # No availability rules for this day, default to unavailable
                is_available = False
        
        if not is_available:
            raise ValidationError("Staff member is not available during this time slot")


class BookingField(models.Model):
    """
    Stores additional fields for bookings.
    Supports both industry-standard fields and business-specific custom fields.
    This allows for dynamic fields based on both industry requirements and business customizations.
    """
    FIELD_TYPE_CHOICES = (
        ('industry', 'Industry Field'),
        ('business', 'Business Custom Field'),
    )
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='fields')
    field_type = models.CharField(max_length=10, choices=FIELD_TYPE_CHOICES, default='industry')
    industry_field = models.ForeignKey(IndustryField, on_delete=models.CASCADE, related_name='booking_values', null=True, blank=True)
    business_field = models.ForeignKey(BusinessCustomField, on_delete=models.CASCADE, related_name='booking_values', null=True, blank=True)
    value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Booking Field"
        verbose_name_plural = "Booking Fields"
    
    def __str__(self):
        if self.field_type == 'industry' and self.industry_field:
            return f"{self.booking} - {self.industry_field.name}: {self.value}"
        elif self.field_type == 'business' and self.business_field:
            return f"{self.booking} - {self.business_field.name}: {self.value}"
        return f"{self.booking} - Unknown Field: {self.value}"
    
    def clean(self):
        # Ensure exactly one field type is provided
        if self.field_type == 'industry' and not self.industry_field:
            raise ValidationError("Industry field must be specified when field type is 'industry'")
        
        if self.field_type == 'business' and not self.business_field:
            raise ValidationError("Business field must be specified when field type is 'business'")
        
        if self.field_type == 'industry' and self.business_field:
            raise ValidationError("Business field should not be specified when field type is 'industry'")
        
        if self.field_type == 'business' and self.industry_field:
            raise ValidationError("Industry field should not be specified when field type is 'business'")
        
        # Ensure no duplicate fields for the same booking
        if self.field_type == 'industry' and self.industry_field:
            duplicates = BookingField.objects.filter(
                booking=self.booking,
                field_type='industry',
                industry_field=self.industry_field
            ).exclude(pk=self.pk)
            
            if duplicates.exists():
                raise ValidationError("This industry field is already added to this booking")
        
        if self.field_type == 'business' and self.business_field:
            duplicates = BookingField.objects.filter(
                booking=self.booking,
                field_type='business',
                business_field=self.business_field
            ).exclude(pk=self.pk)
            
            if duplicates.exists():
                raise ValidationError("This business field is already added to this booking")
    
    def get_field_name(self):
        """Return the name of the field regardless of type"""
        if self.field_type == 'industry' and self.industry_field:
            return self.industry_field.name
        elif self.field_type == 'business' and self.business_field:
            return self.business_field.name
        return "Unknown Field"
    
    def get_field_type(self):
        """Return the actual field type (text, number, etc.) regardless of source"""
        if self.field_type == 'industry' and self.industry_field:
            return self.industry_field.field_type
        elif self.field_type == 'business' and self.business_field:
            return self.business_field.field_type
        return None


class BookingReminder(models.Model):
    """
    Tracks reminders sent for bookings.
    """
    REMINDER_TYPE_CHOICES = (
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('voice', 'Voice Call'),
    )
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='reminders')
    reminder_type = models.CharField(max_length=10, choices=REMINDER_TYPE_CHOICES)
    scheduled_time = models.DateTimeField()
    sent_time = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ), default='pending')
    external_id = models.CharField(max_length=100, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_time']
    
    def __str__(self):
        return f"{self.booking} - {self.get_reminder_type_display()} - {self.status}"
    
    def mark_sent(self, external_id=None):
        """
        Mark a reminder as sent.
        """
        self.status = 'sent'
        self.sent_time = timezone.now()
        if external_id:
            self.external_id = external_id
        self.save(update_fields=['status', 'sent_time', 'external_id', 'updated_at'])
    
    def mark_failed(self, error_message=None):
        """
        Mark a reminder as failed.
        """
        self.status = 'failed'
        if error_message:
            self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated_at'])


# BookingAvailability model has been replaced by the more flexible StaffAvailability model
# Business-wide availability can be implemented using a special "business" staff member
# or by creating availability records for all staff members


class BookingServiceItem(models.Model):
    """
    Associates service items with bookings.
    Allows tracking which specific service items were selected for a booking.
    """
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='service_items')
    service_item = models.ForeignKey(ServiceItem, on_delete=models.CASCADE, related_name='booking_items')
    quantity = models.PositiveIntegerField(default=1)
    price_at_booking = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price of the item at the time of booking")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Booking Service Item"
        verbose_name_plural = "Booking Service Items"
        unique_together = ['booking', 'service_item']
    
    def __str__(self):
        return f"{self.booking} - {self.service_item.name} (x{self.quantity})"
    
    def save(self, *args, **kwargs):
        # If price_at_booking is not set, calculate it based on the service item's pricing rules
        if not self.price_at_booking and self.service_item:
            # Get base price from service offering if available
            base_price = None
            if self.booking.service_offering:
                base_price = self.booking.service_offering.price
                
                # Check if this item is associated with this offering for any special pricing
                try:
                    offering_item = ServiceOfferingItem.objects.get(
                        service_offering=self.booking.service_offering,
                        service_item=self.service_item
                    )
                    # Could apply special pricing rules based on the offering association here
                except ServiceOfferingItem.DoesNotExist:
                    pass
                    
            self.price_at_booking = self.service_item.calculate_price(base_price, self.quantity)
        super().save(*args, **kwargs)
