// booking-preferences.js - Manage booking event types and reminder types

document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                     document.querySelector('meta[name="csrf-token"]')?.content;
    
    // Initialize modals
    const editEventModal = new bootstrap.Modal(document.getElementById('editEventModal'));
    const editReminderModal = new bootstrap.Modal(document.getElementById('editReminderModal'));
    
    // Event Type Toggle Handlers
    document.querySelectorAll('.event-enabled-toggle').forEach(toggle => {
        toggle.addEventListener('change', async function() {
            const eventId = this.dataset.eventId;
            const isEnabled = this.checked;
            
            await updateEventType(eventId, { is_enabled: isEnabled });
            
            // Enable/disable related toggles
            const row = this.closest('tr');
            const timelineToggle = row.querySelector('.event-timeline-toggle');
            const reasonToggle = row.querySelector('.event-reason-toggle');
            
            timelineToggle.disabled = !isEnabled;
            reasonToggle.disabled = !isEnabled;
        });
    });
    
    document.querySelectorAll('.event-timeline-toggle').forEach(toggle => {
        toggle.addEventListener('change', async function() {
            const eventId = this.dataset.eventId;
            const showInTimeline = this.checked;
            
            await updateEventType(eventId, { show_in_timeline: showInTimeline });
        });
    });
    
    document.querySelectorAll('.event-reason-toggle').forEach(toggle => {
        toggle.addEventListener('change', async function() {
            const eventId = this.dataset.eventId;
            const requiresReason = this.checked;
            
            await updateEventType(eventId, { requires_reason: requiresReason });
        });
    });
    
    // Edit Event Type Button
    document.querySelectorAll('.edit-event-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const eventId = this.dataset.eventId;
            const eventName = this.dataset.eventName;
            const eventIcon = this.dataset.eventIcon;
            const eventColor = this.dataset.eventColor;
            
            document.getElementById('editEventId').value = eventId;
            document.getElementById('editEventName').value = eventName;
            document.getElementById('editEventIcon').value = eventIcon;
            document.getElementById('editEventColor').value = eventColor;
            
            editEventModal.show();
        });
    });
    
    // Save Event Type Changes
    document.getElementById('saveEventBtn').addEventListener('click', async function() {
        const eventId = document.getElementById('editEventId').value;
        const name = document.getElementById('editEventName').value;
        const icon = document.getElementById('editEventIcon').value;
        const color = document.getElementById('editEventColor').value;
        
        if (!name || !icon || !color) {
            showAlert('danger', 'Please fill in all fields');
            return;
        }
        
        this.disabled = true;
        this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';
        
        const success = await updateEventType(eventId, { name, icon, color });
        
        if (success) {
            editEventModal.hide();
            setTimeout(() => window.location.reload(), 1000);
        }
        
        this.disabled = false;
        this.innerHTML = '<i class="fas fa-save me-2"></i>Save Changes';
    });
    
    // Reminder Type Toggle Handlers
    document.querySelectorAll('.reminder-enabled-toggle').forEach(toggle => {
        toggle.addEventListener('change', async function() {
            const reminderId = this.dataset.reminderId;
            const isEnabled = this.checked;
            
            await updateReminderType(reminderId, { is_enabled: isEnabled });
            
            // Enable/disable hours input
            const row = this.closest('tr');
            const hoursInput = row.querySelector('.reminder-hours-input');
            hoursInput.disabled = !isEnabled;
        });
    });
    
    // Reminder Hours Input Handler (with debounce)
    let hoursTimeout;
    document.querySelectorAll('.reminder-hours-input').forEach(input => {
        input.addEventListener('change', function() {
            clearTimeout(hoursTimeout);
            const reminderId = this.dataset.reminderId;
            const hours = parseInt(this.value);
            
            if (hours < 1 || hours > 168) {
                showAlert('danger', 'Hours must be between 1 and 168');
                return;
            }
            
            hoursTimeout = setTimeout(async () => {
                await updateReminderType(reminderId, { default_hours_before: hours });
            }, 500);
        });
    });
    
    // Edit Reminder Type Button
    document.querySelectorAll('.edit-reminder-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const reminderId = this.dataset.reminderId;
            const reminderName = this.dataset.reminderName;
            const reminderIcon = this.dataset.reminderIcon;
            
            document.getElementById('editReminderId').value = reminderId;
            document.getElementById('editReminderName').value = reminderName;
            document.getElementById('editReminderIcon').value = reminderIcon;
            
            editReminderModal.show();
        });
    });
    
    // Save Reminder Type Changes
    document.getElementById('saveReminderBtn').addEventListener('click', async function() {
        const reminderId = document.getElementById('editReminderId').value;
        const name = document.getElementById('editReminderName').value;
        const icon = document.getElementById('editReminderIcon').value;
        
        if (!name || !icon) {
            showAlert('danger', 'Please fill in all fields');
            return;
        }
        
        this.disabled = true;
        this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';
        
        const success = await updateReminderType(reminderId, { name, icon });
        
        if (success) {
            editReminderModal.hide();
            setTimeout(() => window.location.reload(), 1000);
        }
        
        this.disabled = false;
        this.innerHTML = '<i class="fas fa-save me-2"></i>Save Changes';
    });
    
    // Helper Functions
    async function updateEventType(eventId, data) {
        try {
            const response = await fetch(`/business/event-type/${eventId}/update/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                showAlert('success', result.message);
                return true;
            } else {
                showAlert('danger', result.message);
                return false;
            }
        } catch (error) {
            showAlert('danger', 'An error occurred while updating event type');
            return false;
        }
    }
    
    async function updateReminderType(reminderId, data) {
        try {
            const response = await fetch(`/business/reminder-type/${reminderId}/update/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                showAlert('success', result.message);
                return true;
            } else {
                showAlert('danger', result.message);
                return false;
            }
        } catch (error) {
            showAlert('danger', 'An error occurred while updating reminder type');
            return false;
        }
    }
    
    function showAlert(type, message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
        alertDiv.style.zIndex = '9999';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alertDiv);
        
        setTimeout(() => {
            alertDiv.remove();
        }, 3000);
    }
});
