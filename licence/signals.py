from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import LicenceKeyUsage, LicencePayment

User = get_user_model()

@receiver(post_save, sender=LicenceKeyUsage)
def log_licence_activation(sender, instance, created, **kwargs):
    """
    Signal handler to log when a license is activated.
    
    This is triggered when a new LicenceKeyUsage record is created.
    """
    if created:
        # Log the license activation (could be expanded to create a more detailed log)
        print(f"License {instance.licence.key} activated by user {instance.user.username} at {timezone.now()}")


@receiver(post_save, sender=LicencePayment)
def log_licence_payment(sender, instance, created, **kwargs):
    """
    Signal handler to log when a license payment is made.
    
    This is triggered when a new LicencePayment record is created.
    """
    if created:
        # Log the license payment
        print(f"License payment of {instance.amount} received from user {instance.user.username} at {timezone.now()}")
