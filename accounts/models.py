from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random
import string
from datetime import timedelta

# Create your models here.

class EmailVerification(models.Model):
    """
    Stores email verification data including OTP codes and verification status.
    Used for verifying business email addresses during registration.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verifications')
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    otp_created_at = models.DateTimeField(auto_now_add=True)
    otp_expiry = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Email Verification"
        verbose_name_plural = "Email Verifications"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.email} - {'Verified' if self.is_verified else 'Not Verified'}"
    
    def save(self, *args, **kwargs):
        # Set OTP expiry time if not already set (30 minutes from creation)
        if not self.otp_expiry:
            self.otp_expiry = timezone.now() + timedelta(minutes=30)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if the OTP has expired"""
        return timezone.now() > self.otp_expiry
    
    @property
    def can_resend(self):
        """Check if a new OTP can be sent (at least 1 minute since last OTP)"""
        return timezone.now() > (self.otp_created_at + timedelta(minutes=1))
    
    @property
    def max_attempts_reached(self):
        """Check if maximum attempts have been reached"""
        return self.attempts >= self.max_attempts
    
    @classmethod
    def generate_otp(cls):
        """Generate a random 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=6))
    
    def refresh_otp(self):
        """Generate a new OTP and reset expiry time"""
        self.otp = self.__class__.generate_otp()
        self.otp_created_at = timezone.now()
        self.otp_expiry = timezone.now() + timedelta(minutes=30)
        self.attempts = 0
        self.save()
        return self.otp





