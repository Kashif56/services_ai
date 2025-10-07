def get_user_business(user):
    if hasattr(user, 'business'):
        return user.business
    elif hasattr(user, 'staff_profile'):
        return user.staff_profile.business
    return None