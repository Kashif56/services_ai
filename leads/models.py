from django.db import models
from django.utils import timezone
from business.models import Business, Industry, IndustryField
from services_ai.utils import generate_id


class LeadStatus(models.TextChoices):
    NEW = 'new', 'New'
    CONTACTED_BY_PHONE = 'contacted_by_phone', 'Contacted By Phone'
    CONTACTED_BY_SMS = 'contacted_by_sms', 'Contacted By SMS'

    QUALIFIED = 'qualified', 'Qualified'
    APPOINTMENT_SCHEDULED = 'appointment_scheduled', 'Appointment Scheduled'
    CONVERTED = 'converted', 'Converted'
    LOST = 'lost', 'Lost'


class LeadSource(models.TextChoices):
    WEBSITE = 'website', 'Website'
    PHONE = 'phone', 'Phone Call'
    REFERRAL = 'referral', 'Referral'
    SOCIAL_MEDIA = 'social_media', 'Social Media'
    OTHER = 'other', 'Other'


class Lead(models.Model):
    """
    Main lead model to store basic lead information.
    Industry-specific data is stored in LeadField model.
    """
    id = models.CharField(primary_key=True, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='leads')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=50, choices=LeadStatus.choices, default=LeadStatus.NEW)
    source = models.CharField(max_length=50, choices=LeadSource.choices, default=LeadSource.WEBSITE)
    notes = models.TextField(blank=True, null=True)

    last_contacted = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.business.name}"
    
    def mark_contacted(self, contact_method):
        """
        Mark the lead as contacted and update the last_contacted timestamp.
        """
        self.status = LeadStatus.CONTACTED_BY_PHONE if contact_method == 'phone' else LeadStatus.CONTACTED_BY_SMS
        self.last_contacted = timezone.now()
        self.save(update_fields=['status', 'last_contacted', 'updated_at'])
    
    def get_full_name(self):
        """
        Return the lead's full name.
        """
        return f"{self.first_name} {self.last_name}"
    
    def get_field_value(self, field_name):
        """
        Get the value of a specific field for this lead.
        """
        try:
            field = self.fields.get(field__slug=field_name)
            return field.value
        except LeadField.DoesNotExist:
            return None
    

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('lead_')
        super().save(*args, **kwargs)


class LeadField(models.Model):
    """
    Stores industry-specific field values for each lead.
    This allows for dynamic fields based on the industry.
    """
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='fields')
    field = models.ForeignKey(IndustryField, on_delete=models.CASCADE, related_name='lead_values')
    value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['lead', 'field']
    
    def __str__(self):
        return f"{self.lead} - {self.field.name}: {self.value}"


class LeadCommunication(models.Model):
    """
    Tracks all communications with a lead (SMS, voice calls, etc.).
    """
    DIRECTION_CHOICES = (
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    )
    
    TYPE_CHOICES = (
        ('sms', 'SMS'),
        ('voice', 'Voice Call'),
        ('email', 'Email'),
        ('webhook', 'Webhook'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('received', 'Received'),
    )
    
    id = models.CharField(primary_key=True, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='communications')
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    comm_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    external_id = models.CharField(max_length=100, blank=True, null=True, help_text='ID from external service (e.g., Twilio)')
    metadata = models.JSONField(blank=True, null=True, help_text='Additional metadata from the communication')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.lead} - {self.get_comm_type_display()} ({self.get_direction_display()})"
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('comm_')
        super().save(*args, **kwargs)


class WebhookEndpoint(models.Model):
    """
    Defines webhook endpoints for receiving leads from external sources.
    """
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='webhook_endpoints')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)
    secret_key = models.CharField(max_length=64, blank=True, null=True, help_text='Secret key for webhook authentication')
    field_mapping = models.JSONField(help_text='Mapping of webhook fields to lead fields')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['business', 'name']
    
    def __str__(self):
        return f"{self.business.name} - {self.name}"


class WebhookLog(models.Model):
    """
    Logs all webhook requests for debugging and auditing.
    """
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='logs')
    request_data = models.JSONField()
    response_data = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    status_code = models.PositiveIntegerField()
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name='webhook_logs')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.endpoint} - {self.status_code} - {self.created_at}"
