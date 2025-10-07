from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from .models import StaffProfile
from bookings.models import StaffMember


def create_staff_user(staff_member, username, email, password, is_active=True):
    """
    Create a User account and StaffProfile for a StaffMember.
    
    Args:
        staff_member: StaffMember instance
        username: Username for the new user account
        email: Email for the new user account
        password: Password for the new user account
        is_active: Whether the staff profile should be active (default: True)
    
    Returns:
        tuple: (user, staff_profile) - The created User and StaffProfile instances
    
    Raises:
        ValidationError: If username or email already exists, or if staff member already has a profile
    """
    # Check if username already exists
    if User.objects.filter(username=username).exists():
        raise ValidationError(f"Username '{username}' already exists")
    
    # Check if email already exists
    if User.objects.filter(email=email).exists():
        raise ValidationError(f"Email '{email}' already exists")
    
    # Check if staff member already has a profile
    if hasattr(staff_member, 'profile'):
        raise ValidationError(f"Staff member '{staff_member.get_full_name()}' already has a user account")
    
    # Create user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=staff_member.first_name,
        last_name=staff_member.last_name
    )
    
    # Add to staff group (create if doesn't exist)
    staff_group, created = Group.objects.get_or_create(name='staff')
    if created:
        # If group was just created, add appropriate permissions
        from django.contrib.contenttypes.models import ContentType
        from django.contrib.auth.models import Permission
        from bookings.models import Booking, BookingStaffAssignment
        
        try:
            # Get content types
            booking_ct = ContentType.objects.get_for_model(Booking)
            assignment_ct = ContentType.objects.get_for_model(BookingStaffAssignment)
            staff_profile_ct = ContentType.objects.get_for_model(StaffProfile)
            
            # Add view permissions
            permissions = []
            try:
                permissions.append(Permission.objects.get(codename='view_booking', content_type=booking_ct))
            except Permission.DoesNotExist:
                pass
            try:
                permissions.append(Permission.objects.get(codename='view_bookingstaffassignment', content_type=assignment_ct))
            except Permission.DoesNotExist:
                pass
            try:
                permissions.append(Permission.objects.get(codename='view_staffprofile', content_type=staff_profile_ct))
            except Permission.DoesNotExist:
                pass
            try:
                permissions.append(Permission.objects.get(codename='change_staffprofile', content_type=staff_profile_ct))
            except Permission.DoesNotExist:
                pass
            
            if permissions:
                staff_group.permissions.set(permissions)
        except Exception:
            # If permissions setup fails, continue anyway
            pass
    
    user.groups.add(staff_group)
    
    # Create staff profile
    staff_profile = StaffProfile.objects.create(
        user=user,
        staff_member=staff_member,
        business=staff_member.business,
        is_active=is_active
    )
    
    return user, staff_profile


def deactivate_staff_user(staff_member):
    """
    Deactivate a staff member's user account and profile.
    
    Args:
        staff_member: StaffMember instance
    
    Returns:
        bool: True if deactivated, False if no profile exists
    """
    try:
        staff_profile = staff_member.profile
        staff_profile.is_active = False
        staff_profile.save()
        
        # Also deactivate the user account
        staff_profile.user.is_active = False
        staff_profile.user.save()
        
        return True
    except StaffProfile.DoesNotExist:
        return False


def activate_staff_user(staff_member):
    """
    Activate a staff member's user account and profile.
    
    Args:
        staff_member: StaffMember instance
    
    Returns:
        bool: True if activated, False if no profile exists
    """
    try:
        staff_profile = staff_member.profile
        staff_profile.is_active = True
        staff_profile.save()
        
        # Also activate the user account
        staff_profile.user.is_active = True
        staff_profile.user.save()
        
        return True
    except StaffProfile.DoesNotExist:
        return False


def delete_staff_user(staff_member):
    """
    Delete a staff member's user account and profile.
    This will cascade delete the StaffProfile and User.
    
    Args:
        staff_member: StaffMember instance
    
    Returns:
        bool: True if deleted, False if no profile exists
    """
    try:
        staff_profile = staff_member.profile
        user = staff_profile.user
        
        # Delete profile first (will cascade)
        staff_profile.delete()
        
        # Delete user
        user.delete()
        
        return True
    except StaffProfile.DoesNotExist:
        return False


def reset_staff_password(staff_member, new_password):
    """
    Reset a staff member's password.
    
    Args:
        staff_member: StaffMember instance
        new_password: New password string
    
    Returns:
        bool: True if password reset, False if no profile exists
    """
    try:
        staff_profile = staff_member.profile
        staff_profile.user.set_password(new_password)
        staff_profile.user.save()
        return True
    except StaffProfile.DoesNotExist:
        return False


def get_staff_user(staff_member):
    """
    Get the User account associated with a StaffMember.
    
    Args:
        staff_member: StaffMember instance
    
    Returns:
        User: The associated User instance, or None if no profile exists
    """
    try:
        return staff_member.profile.user
    except StaffProfile.DoesNotExist:
        return None


def has_staff_account(staff_member):
    """
    Check if a staff member has a user account.
    
    Args:
        staff_member: StaffMember instance
    
    Returns:
        bool: True if staff member has a user account, False otherwise
    """
    return hasattr(staff_member, 'profile')
