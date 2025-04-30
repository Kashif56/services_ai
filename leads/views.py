from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from django.contrib import messages
from .models import Lead, LeadStatus, LeadSource
from business.models import Business

@login_required
def index(request):
    # Get the user's business
    business = request.user.business
    
    # Get filter parameters
    status = request.GET.get('status', '')
    source = request.GET.get('source', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('search', '')
    
    # Start with all leads for the business
    leads = Lead.objects.filter(business=business)
    
    # Apply filters
    if status:
        leads = leads.filter(status=status)
    
    if source:
        leads = leads.filter(source=source)
    
    if date_from:
        leads = leads.filter(created_at__gte=date_from)
    
    if date_to:
        # Add one day to include the end date
        leads = leads.filter(created_at__lte=date_to + ' 23:59:59')
    
    if search_query:
        leads = leads.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    context = {
        'leads': leads,
        'lead_statuses': LeadStatus.choices,
        'lead_sources': LeadSource.choices,
        'current_status': status,
        'current_source': source,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
    }
    
    return render(request, 'leads/index.html', context)

@login_required
def lead_detail(request, lead_id):
    # Get the user's business
    business = request.user.business
    
    # Get the lead, ensuring it belongs to the user's business
    lead = get_object_or_404(Lead, id=lead_id, business=business)
    
    # Get all communications for this lead
    communications = lead.communications.all().order_by('-created_at')
    
    # Get all fields for this lead
    lead_fields = lead.fields.all().select_related('field')
    
    context = {
        'lead': lead,
        'communications': communications,
        'lead_fields': lead_fields,
        'lead_statuses': LeadStatus.choices,
    }
    
    return render(request, 'leads/detail.html', context)

@login_required
def create_lead(request):
    # Get the user's business
    business = request.user.business
    
    if request.method == 'POST':
        # Extract basic lead information
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        status = request.POST.get('status')
        source = request.POST.get('source')
        notes = request.POST.get('notes')
        
        # Create the lead
        lead = Lead.objects.create(
            business=business,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            status=status,
            source=source,
            notes=notes
        )
        
        messages.success(request, 'Lead created successfully!')
        return redirect('leads:lead_detail', lead_id=lead.id)
    
    # Provide a limited set of the most relevant statuses for new leads
    limited_statuses = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('qualified', 'Qualified'),
        ('appointment_scheduled', 'Appointment Scheduled')
    ]
    
    # Provide a limited set of the most common lead sources
    limited_sources = [
        ('website', 'Website'),
        ('phone', 'Phone Call'),
        ('referral', 'Referral'),
        ('social_media', 'Social Media'),
        ('other', 'Other')
    ]
    
    context = {
        'lead_statuses': limited_statuses,
        'lead_sources': limited_sources,
    }
    
    return render(request, 'leads/create.html', context)

@login_required
def edit_lead(request, lead_id):
    # Get the user's business
    business = request.user.business
    
    # Get the lead, ensuring it belongs to the user's business
    lead = get_object_or_404(Lead, id=lead_id, business=business)
    
    # Provide a limited set of the most relevant statuses for leads
    limited_statuses = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('qualified', 'Qualified'),
        ('appointment_scheduled', 'Appointment Scheduled'),
        ('converted', 'Converted'),
        ('lost', 'Lost')
    ]
    
    # Provide a limited set of the most common lead sources
    limited_sources = [
        ('website', 'Website'),
        ('phone', 'Phone Call'),
        ('referral', 'Referral'),
        ('social_media', 'Social Media'),
        ('other', 'Other')
    ]
    
    if request.method == 'POST':
        # Extract updated lead information
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        status = request.POST.get('status')
        source = request.POST.get('source')
        notes = request.POST.get('notes')
        
        # Update the lead
        lead.first_name = first_name
        lead.last_name = last_name
        lead.email = email
        lead.phone = phone
        lead.status = status
        lead.source = source
        lead.notes = notes
        lead.save()
        
        messages.success(request, 'Lead updated successfully!')
        return redirect('leads:lead_detail', lead_id=lead.id)
    
    context = {
        'lead': lead,
        'lead_statuses': limited_statuses,
        'lead_sources': limited_sources,
        'is_edit': True
    }
    
    return render(request, 'leads/edit.html', context)
