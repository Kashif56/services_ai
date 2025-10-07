# Staff Portal Module

## Overview
The Staff Portal provides limited access to staff members, allowing them to view their assigned bookings and manage their profile while restricting access to business management features.

## Features

### 1. StaffProfile Model
Links User accounts to StaffMember records, enabling staff login with controlled permissions.

**Key Fields:**
- `user` - OneToOne link to Django User
- `staff_member` - OneToOne link to StaffMember
- `business` - ForeignKey to Business
- `is_active` - Active status flag

### 2. Access Control Middleware
`StaffAccessMiddleware` automatically restricts staff users to allowed pages:

**Allowed Access:**
- Core pages (landing, about, contact)
- Auth pages (login, logout, profile, settings, change password)
- Staff portal pages (`/staff/*`)
- Their own staff detail page
- Static and media files

**Restricted Access:**
All other business management pages are blocked. Attempts to access restricted pages redirect to the staff member's detail page.

### 3. User Groups
Three user groups with distinct access levels:

- **business** - Business owners with full access
- **staff** - Staff members with limited access
- **customer** - Customers with access to their bookings/invoices

### 4. Staff Views
- `staff_dashboard` - Redirects to staff detail page
- `staff_bookings` - Lists all assigned bookings with filtering

## Installation

### Step 1: Run Migrations
```bash
python manage.py makemigrations staff
python manage.py migrate
```

### Step 2: Create User Groups
```bash
python manage.py create_user_groups
```

## Usage

### Creating Staff User Accounts

#### Method 1: Using Utility Functions (Recommended)
```python
from staff.utils import create_staff_user
from bookings.models import StaffMember

# Get the staff member
staff_member = StaffMember.objects.get(id='staff_id')

# Create user account
user, staff_profile = create_staff_user(
    staff_member=staff_member,
    username='john.doe',
    email='john.doe@example.com',
    password='secure_password123',
    is_active=True
)
```

#### Method 2: Manual Creation
```python
from django.contrib.auth.models import User, Group
from staff.models import StaffProfile
from bookings.models import StaffMember

# Create user
user = User.objects.create_user(
    username='john.doe',
    email='john.doe@example.com',
    password='secure_password123',
    first_name='John',
    last_name='Doe'
)

# Add to staff group
staff_group = Group.objects.get(name='staff')
user.groups.add(staff_group)

# Create staff profile
staff_member = StaffMember.objects.get(id='staff_id')
staff_profile = StaffProfile.objects.create(
    user=user,
    staff_member=staff_member,
    business=staff_member.business,
    is_active=True
)
```

### Managing Staff Accounts

#### Deactivate Staff Account
```python
from staff.utils import deactivate_staff_user
from bookings.models import StaffMember

staff_member = StaffMember.objects.get(id='staff_id')
deactivate_staff_user(staff_member)
```

#### Activate Staff Account
```python
from staff.utils import activate_staff_user
from bookings.models import StaffMember

staff_member = StaffMember.objects.get(id='staff_id')
activate_staff_user(staff_member)
```

#### Reset Password
```python
from staff.utils import reset_staff_password
from bookings.models import StaffMember

staff_member = StaffMember.objects.get(id='staff_id')
reset_staff_password(staff_member, 'new_secure_password')
```

#### Delete Staff Account
```python
from staff.utils import delete_staff_user
from bookings.models import StaffMember

staff_member = StaffMember.objects.get(id='staff_id')
delete_staff_user(staff_member)
```

#### Check if Staff Has Account
```python
from staff.utils import has_staff_account, get_staff_user
from bookings.models import StaffMember

staff_member = StaffMember.objects.get(id='staff_id')

if has_staff_account(staff_member):
    user = get_staff_user(staff_member)
    print(f"Staff has account: {user.username}")
else:
    print("Staff does not have an account")
```

## URL Structure

### Staff Portal URLs
- `/staff/` - Staff dashboard (redirects to detail page)
- `/staff/bookings/` - View assigned bookings

### Accessible URLs for Staff
- `/` - Landing page
- `/accounts/login/` - Login
- `/accounts/logout/` - Logout
- `/accounts/profile/` - Profile management
- `/accounts/settings/` - Account settings
- `/accounts/change-password/` - Change password
- `/business/staff/<staff_id>/` - Their own staff detail page

## Permissions

Staff users have the following Django permissions:
- `view_booking` - View bookings
- `view_bookingstaffassignment` - View booking assignments
- `view_staffprofile` - View staff profile
- `change_staffprofile` - Edit staff profile

## Security Considerations

1. **Middleware Order**: `StaffAccessMiddleware` must be placed after `AuthenticationMiddleware` in `settings.py`

2. **Superuser Bypass**: Superusers bypass all middleware restrictions

3. **Group Membership**: Access control is based on the 'staff' group membership

4. **Profile Validation**: StaffProfile validates that staff_member belongs to the same business

5. **Password Security**: Always use strong passwords when creating staff accounts

## Templates

### Staff Bookings Template
Location: `templates/staff/bookings.html`

Features:
- Card-based booking display
- Status badges with color coding
- Filtering by status and date range
- Responsive design
- Quick access to booking details

## Future Enhancements

1. **Staff Dashboard**: Dedicated dashboard with statistics and upcoming bookings
2. **Booking Status Updates**: Allow staff to update booking status
3. **Availability Management**: Staff can manage their own availability
4. **Notifications**: Real-time notifications for new bookings
5. **Mobile App**: Mobile application for staff members
6. **Time Tracking**: Track time spent on bookings
7. **Performance Metrics**: View personal performance statistics

## Troubleshooting

### Staff User Can't Login
- Verify user account is active: `user.is_active = True`
- Verify staff profile is active: `staff_profile.is_active = True`
- Check user is in 'staff' group
- Verify StaffProfile exists for the user

### Staff User Can Access Restricted Pages
- Verify middleware is properly configured in `settings.py`
- Check middleware order (must be after AuthenticationMiddleware)
- Verify user is in 'staff' group
- Clear browser cache and cookies

### Permission Errors
- Run `python manage.py create_user_groups` to ensure groups and permissions exist
- Verify staff group has correct permissions
- Check that migrations have been applied

### Staff Profile Creation Fails
- Ensure staff_member belongs to the specified business
- Verify staff_member doesn't already have a profile
- Check that username and email are unique

## API Reference

### Utility Functions

#### `create_staff_user(staff_member, username, email, password, is_active=True)`
Creates a user account and staff profile for a staff member.

**Returns:** `(user, staff_profile)` tuple

**Raises:** `ValidationError` if validation fails

#### `deactivate_staff_user(staff_member)`
Deactivates a staff member's account.

**Returns:** `bool` - True if successful, False if no profile exists

#### `activate_staff_user(staff_member)`
Activates a staff member's account.

**Returns:** `bool` - True if successful, False if no profile exists

#### `delete_staff_user(staff_member)`
Deletes a staff member's user account and profile.

**Returns:** `bool` - True if successful, False if no profile exists

#### `reset_staff_password(staff_member, new_password)`
Resets a staff member's password.

**Returns:** `bool` - True if successful, False if no profile exists

#### `get_staff_user(staff_member)`
Gets the User instance for a staff member.

**Returns:** `User` instance or `None`

#### `has_staff_account(staff_member)`
Checks if a staff member has a user account.

**Returns:** `bool`

## Support

For issues or questions, please refer to the main project documentation or contact the development team.
