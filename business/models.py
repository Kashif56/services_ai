from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
import uuid
from django.conf import settings
from decimal import Decimal



BASE_URL = settings.BASE_URL

CRM_CHOICES = (
    ('hubspot', 'HubSpot'),
    ('salesforce', 'Salesforce'),
    ('zoho', 'Zoho CRM'),
    ('pipedrive', 'Pipedrive'),
    ('custom', 'Custom CRM'),
)

class Industry(models.Model):
    """
    Represents different business domains (cleaning, roofing, salons, dental, etc.)
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True, help_text="CSS class for icon")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Industry"
        verbose_name_plural = "Industries"
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Business(models.Model):
    """
    Represents a business entity that belongs to a specific industry.
    Each business can have its own configuration and customization.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='business')
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE, related_name='businesses')
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    logo = models.ImageField(upload_to='business_logos/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Business"
        verbose_name_plural = "Businesses"
        ordering = ['-created_at']

    def __str__(self):
        return self.name
    

    def get_lead_webhook_url(self):
        return f"{BASE_URL}/leads/webhook/{self.id}/"


FIELD_TYPES = (
    ('text', 'Text'),
    ('number', 'Number'),
    ('select', 'Select'),
    ('date', 'Date'),
    ('time', 'Time'),
    ('datetime', 'Date and Time'),
    ('boolean', 'Yes/No'),
    ('email', 'Email'),
    ('phone', 'Phone Number'),
    ('url', 'URL'),
    ('textarea', 'Text Area'),
)


class IndustryField(models.Model):
    """
    Dynamic fields tied to each industry (e.g., "square feet" for cleaning).
    These fields define the data that needs to be collected for each industry.
    """
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE, related_name='fields')
    name = models.CharField(max_length=100)  # e.g., "Square Feet"
    slug = models.SlugField(max_length=120, blank=True)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    options = models.JSONField(blank=True, null=True)  # used for select dropdowns
    placeholder = models.CharField(max_length=200, blank=True, null=True)
    help_text = models.CharField(max_length=255, blank=True, null=True)
    required = models.BooleanField(default=True)
    default_value = models.CharField(max_length=255, blank=True, null=True)
    validation_regex = models.CharField(max_length=255, blank=True, null=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Industry Field"
        verbose_name_plural = "Industry Fields"
        ordering = ['display_order', 'name']
        unique_together = ['industry', 'slug']

    def __str__(self):
        return f"{self.industry.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class BusinessCustomField(models.Model):
    """
    Override or add more fields at a business level (optional).
    Allows businesses to customize their own fields beyond the industry defaults.
    """
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='custom_fields')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    options = models.JSONField(blank=True, null=True)
    placeholder = models.CharField(max_length=200, blank=True, null=True)
    help_text = models.CharField(max_length=255, blank=True, null=True)
    required = models.BooleanField(default=True)
    default_value = models.CharField(max_length=255, blank=True, null=True)
    validation_regex = models.CharField(max_length=255, blank=True, null=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Business Custom Field"
        verbose_name_plural = "Business Custom Fields"
        ordering = ['display_order', 'name']
        unique_together = ['business', 'slug']

    def __str__(self):
        return f"{self.business.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class BusinessConfiguration(models.Model):
    """
    Business-specific configuration settings.
    """
    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name='configuration')

    # Voice Configuration
    voice_enabled = models.BooleanField(default=True)
    initial_response_delay = models.PositiveIntegerField(default=5, help_text="Delay in minutes before first contact")


    # Twilio Configuration for SMS
    twilio_phone_number = models.CharField(max_length=20, blank=True, null=True)
    twilio_sid = models.CharField(max_length=255, blank=True, null=True)
    twilio_auth_token = models.CharField(max_length=255, blank=True, null=True)
    

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Configuration for {self.business.name}"
    
    



class ServiceOffering(models.Model):
    """
    Represents a service offered by a business.
    This is a simplified model for managing service offerings directly.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='service_offerings')
    name = models.CharField(max_length=100)
    identifier = models.SlugField(max_length=120, blank=True, help_text="Unique identifier for this service (e.g., number_of_bedrooms)")
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    icon = models.CharField(max_length=50, default="concierge-bell", help_text="FontAwesome icon name")
    color = models.CharField(max_length=20, default="#6366f1", help_text="Color code for the service icon")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Service Offering"
        verbose_name_plural = "Service Offerings"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.business.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.identifier:
            # Convert name to snake_case for identifier
            self.identifier = slugify(self.name).replace('-', '_')
        super().save(*args, **kwargs)


# Association model to link ServiceItems with ServiceOfferings
class ServiceOfferingItem(models.Model):
    """
    Links service items to service offerings.
    This allows for flexible composition of service offerings with reusable items.
    """
    service_offering = models.ForeignKey(ServiceOffering, on_delete=models.CASCADE, related_name='offering_items')
    service_item = models.ForeignKey('ServiceItem', on_delete=models.CASCADE, related_name='offering_associations')
    is_default = models.BooleanField(default=False, help_text="Whether this item is included by default with this offering")
    is_required = models.BooleanField(default=False, help_text="Whether this item is required for this offering")
    display_order = models.PositiveIntegerField(default=0, help_text="Order to display items in the offering")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Service Offering Item"
        verbose_name_plural = "Service Offering Items"
        ordering = ['service_offering', 'display_order', 'service_item__name']
        unique_together = ['service_offering', 'service_item']
    
    def __str__(self):
        return f"{self.service_offering.name} - {self.service_item.name}"


# ServicePackage model removed as packages are not offered at the moment


class ServiceItem(models.Model):
    """
    Represents individual service items that can be added to service offerings.
    This allows for modular and dynamic pricing based on selected items.
    Items are independent of specific service offerings for maximum flexibility.
    """
    PRICE_TYPE_CHOICES = (
        ('fixed', 'Fixed Price'),
        ('percentage', 'Percentage of Base Price'),
        ('hourly', 'Hourly Rate'),
        ('per_unit', 'Per Unit'),
    )
    
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='service_items')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price_type = models.CharField(max_length=20, choices=PRICE_TYPE_CHOICES, default='fixed')
    price_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    is_optional = models.BooleanField(default=True, help_text="Whether this item is optional or required by default")
    is_active = models.BooleanField(default=True)
    duration_minutes = models.PositiveIntegerField(default=0, help_text="Additional time required for this item")
    max_quantity = models.PositiveIntegerField(default=1, help_text="Maximum quantity allowed for this item")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Service Item"
        verbose_name_plural = "Service Items"
        ordering = ['business', 'name']
    
    def __str__(self):
        return f"{self.business.name} - {self.name}"
    
    def calculate_price(self, base_price=None, quantity=1):
        """
        Calculate the price for this service item based on its price type.
        """
        if quantity <= 0:
            return Decimal('0.00')
            
        if self.price_type == 'fixed':
            return self.price_value * quantity
        elif self.price_type == 'percentage' and base_price:
            return (base_price * self.price_value / 100) * quantity
        elif self.price_type == 'hourly':
            # Convert duration_minutes to hours and multiply by hourly rate
            hours = self.duration_minutes / 60
            return self.price_value * hours * quantity
        elif self.price_type == 'per_unit':
            return self.price_value * quantity
        return Decimal('0.00')
