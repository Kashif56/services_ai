from django.db import models
from django.contrib.auth.models import User
from bookings.models import StaffMember
from business.models import Business
from django.core.exceptions import ValidationError


class StaffProfile(models.Model):
    """
    Links a User account to a StaffMember and Business.
    This allows staff members to have login access with limited permissions.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    staff_member = models.OneToOneField(StaffMember, on_delete=models.CASCADE, related_name='profile')
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='staff_profiles')
    is_active = models.BooleanField(default=True, help_text="Whether this staff profile is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Staff Profile"
        verbose_name_plural = "Staff Profiles"
        ordering = ['business', 'staff_member']
    
    def __str__(self):
        return f"{self.user.username} - {self.staff_member.get_full_name()} ({self.business.name})"
    
    def clean(self):
        # Ensure staff_member belongs to the same business
        if self.staff_member.business != self.business:
            raise ValidationError("Staff member must belong to the same business")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
