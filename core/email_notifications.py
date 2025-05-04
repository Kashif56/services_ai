"""
Email notification utilities for leads and invoices.
This module provides functions to send email notifications when leads or invoices are created.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

from business.models import SMTPConfig
from leads.models import Lead
from invoices.models import Invoice

logger = logging.getLogger(__name__)

def get_smtp_config(business):
    """
    Get SMTP configuration for a business.
    If no configuration exists, return None.
    
    Args:
        business: The Business object
        
    Returns:
        SMTPConfig object or None
    """
    try:
        return SMTPConfig.objects.get(business=business)
    except SMTPConfig.DoesNotExist:
        logger.warning(f"No SMTP configuration found for business {business.name} (ID: {business.id})")
        return None

def send_email(smtp_config, recipient_email, subject, html_content, reply_to=None):
    """
    Send an email using the provided SMTP configuration.
    
    Args:
        smtp_config: SMTPConfig object
        recipient_email: Email address of the recipient
        subject: Email subject
        html_content: HTML content of the email
        reply_to: Reply-to email address (optional)
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not smtp_config:
        logger.error("Cannot send email: No SMTP configuration provided")
        return False
    
    try:
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = smtp_config.from_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Set reply-to if provided, otherwise use the one from SMTP config
        if reply_to:
            msg['Reply-To'] = reply_to
        else:
            msg['Reply-To'] = smtp_config.reply_to
        
        # Attach HTML content
        msg.attach(MIMEText(html_content, 'html'))
        
        # Plain text version (fallback)
        text_content = strip_tags(html_content)
        msg.attach(MIMEText(text_content, 'plain'))
        
        # Connect to SMTP server and send email
        server = smtplib.SMTP(smtp_config.host, smtp_config.port)
        server.starttls()  # Start TLS encryption
        server.login(smtp_config.username, smtp_config.password)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
        return False

def send_lead_notification(lead_id):
    """
    Send email notifications when a new lead is created.
    Sends emails to both the business owner and the lead.
    
    Args:
        lead_id: ID of the Lead
        
    Returns:
        tuple: (business_email_sent, lead_email_sent) - booleans indicating if emails were sent
    """
    try:
        lead = Lead.objects.get(id=lead_id)
        business = lead.business
        
        # Get SMTP configuration
        smtp_config = get_smtp_config(business)
        if not smtp_config:
            return False, False
        
        # Send email to business owner
        business_email_sent = send_business_lead_notification(lead, smtp_config)
        
        # Send email to lead
        lead_email_sent = send_lead_confirmation(lead, smtp_config)
        
        return business_email_sent, lead_email_sent
    
    except Lead.DoesNotExist:
        logger.error(f"Lead with ID {lead_id} does not exist")
        return False, False
    except Exception as e:
        logger.error(f"Error sending lead notification emails: {str(e)}")
        return False, False

def send_business_lead_notification(lead, smtp_config):
    """
    Send a notification email to the business owner about a new lead.
    
    Args:
        lead: Lead object
        smtp_config: SMTPConfig object
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    business = lead.business
    
    # Prepare context for email template
    context = {
        'business_name': business.name,
        'lead_name': lead.get_full_name(),
        'lead_email': lead.email,
        'lead_phone': lead.phone,
        'lead_source': lead.get_source_display(),
        'lead_created_at': lead.created_at,
    }
    
    # Render email template
    html_content = render_to_string('emails/new_lead_business_notification.html', context)
    
    # Send email
    subject = f"New Lead: {lead.get_full_name()} - {business.name}"
    return send_email(smtp_config, business.email, subject, html_content)

def send_lead_confirmation(lead, smtp_config):
    """
    Send a confirmation email to the lead.
    
    Args:
        lead: Lead object
        smtp_config: SMTPConfig object
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    business = lead.business
    
    # Prepare context for email template
    context = {
        'lead_name': lead.get_full_name(),
        'business_name': business.name,
        'business_phone': business.phone_number,
        'business_email': business.email,
        'business_website': business.website,
    }
    
    # Render email template
    html_content = render_to_string('emails/lead_confirmation.html', context)
    
    # Send email
    subject = f"Thank you for your interest in {business.name}"
    return send_email(smtp_config, lead.email, subject, html_content, reply_to=business.email)

def send_invoice_notification(invoice_id):
    """
    Send email notifications when a new invoice is created.
    Sends emails to both the business owner and the client.
    
    Args:
        invoice_id: ID of the Invoice
        
    Returns:
        tuple: (business_email_sent, client_email_sent) - booleans indicating if emails were sent
    """
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        booking = invoice.booking
        business = booking.business
        client_email = booking.email
        
        # Get SMTP configuration
        smtp_config = get_smtp_config(business)
        if not smtp_config:
            return False, False
        
        # Send email to business owner
        business_email_sent = send_business_invoice_notification(invoice, smtp_config)
        
        # Send email to client
        client_email_sent = send_client_invoice_notification(invoice, smtp_config)
        
        return business_email_sent, client_email_sent
    
    except Invoice.DoesNotExist:
        logger.error(f"Invoice with ID {invoice_id} does not exist")
        return False, False
    except Exception as e:
        logger.error(f"Error sending invoice notification emails: {str(e)}")
        return False, False

def send_business_invoice_notification(invoice, smtp_config):
    """
    Send a notification email to the business owner about a new invoice.
    
    Args:
        invoice: Invoice object
        smtp_config: SMTPConfig object
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    booking = invoice.booking
    business = booking.business
    
    # Prepare context for email template
    context = {
        'business_name': business.name,
        'invoice_number': invoice.invoice_number,
        'booking_name': booking.name,
        'client_name': booking.name,
        'client_email': booking.email,
        'invoice_status': invoice.get_status_display(),
        'invoice_due_date': invoice.due_date,
        'invoice_created_at': invoice.created_at,
    }
    
    # Render email template
    html_content = render_to_string('emails/new_invoice_business_notification.html', context)
    
    # Send email
    subject = f"New Invoice #{invoice.invoice_number} Created - {business.name}"
    return send_email(smtp_config, business.email, subject, html_content)

def send_client_invoice_notification(invoice, smtp_config):
    """
    Send a notification email to the client about a new invoice.
    
    Args:
        invoice: Invoice object
        smtp_config: SMTPConfig object
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    booking = invoice.booking
    business = booking.business
    client_email = booking.email
    
    # Get invoice preview URL
    invoice_preview_url = invoice.get_preview_url()
    
    # Prepare context for email template
    context = {
        'client_name': booking.name,
        'business_name': business.name,
        'invoice_number': invoice.invoice_number,
        'booking_name': booking.name,
        'invoice_status': invoice.get_status_display(),
        'invoice_due_date': invoice.due_date,
        'business_phone': business.phone_number,
        'business_email': business.email,
        'invoice_preview_url': invoice_preview_url,
        'booking': booking,  # Pass the entire booking object for detailed information
    }
    
    # Render email template
    html_content = render_to_string('emails/invoice_client_notification.html', context)
    
    # Send email
    subject = f"Invoice #{invoice.invoice_number} from {business.name}"
    return send_email(smtp_config, client_email, subject, html_content, reply_to=business.email)
