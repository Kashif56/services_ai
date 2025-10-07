// bookings-detail.js - Enhance the booking detail page

document.addEventListener('DOMContentLoaded', function() {
    // Get booking ID from URL
    const bookingId = window.location.pathname.split('/').filter(Boolean).pop();
    
    // Get CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                     document.querySelector('meta[name="csrf-token"]')?.content;
    
    // Initialize modals
    const cancelModal = new bootstrap.Modal(document.getElementById('cancelBookingModal'));
    const rescheduleModal = new bootstrap.Modal(document.getElementById('rescheduleBookingModal'));
    
    // Cancel Booking Functionality
    const cancelBookingBtn = document.getElementById('cancelBookingBtn');
    const confirmCancelBtn = document.getElementById('confirmCancelBtn');
    const cancellationReason = document.getElementById('cancellationReason');
    
    if (cancelBookingBtn) {
        cancelBookingBtn.addEventListener('click', function(e) {
            e.preventDefault();
            cancelModal.show();
        });
    }
    
    if (confirmCancelBtn) {
        confirmCancelBtn.addEventListener('click', async function() {
            const reason = cancellationReason.value.trim();
            
            if (!reason) {
                cancellationReason.classList.add('is-invalid');
                return;
            }
            
            cancellationReason.classList.remove('is-invalid');
            confirmCancelBtn.disabled = true;
            confirmCancelBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Cancelling...';
            
            try {
                const response = await fetch(`/bookings/${bookingId}/cancel/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ reason })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    cancelModal.hide();
                    showAlert('success', data.message);
                    setTimeout(() => window.location.reload(), 1500);
                } else {
                    showAlert('danger', data.message);
                    confirmCancelBtn.disabled = false;
                    confirmCancelBtn.innerHTML = '<i class="fas fa-times me-2"></i>Cancel Booking';
                }
            } catch (error) {
                showAlert('danger', 'An error occurred while cancelling the booking');
                confirmCancelBtn.disabled = false;
                confirmCancelBtn.innerHTML = '<i class="fas fa-times me-2"></i>Cancel Booking';
            }
        });
    }
    
    // Reschedule Booking Functionality
    const rescheduleBookingBtn = document.getElementById('rescheduleBookingBtn');
    const checkAvailabilityBtn = document.getElementById('checkAvailabilityBtn');
    const backToDateBtn = document.getElementById('backToDateBtn');
    const backToTimeslotsBtn = document.getElementById('backToTimeslotsBtn');
    const confirmRescheduleBtn = document.getElementById('confirmRescheduleBtn');
    const rescheduleDate = document.getElementById('rescheduleDate');
    const rescheduleReason = document.getElementById('rescheduleReason');
    
    let selectedSlot = null;
    
    if (rescheduleBookingBtn) {
        rescheduleBookingBtn.addEventListener('click', function(e) {
            e.preventDefault();
            // Set minimum date to tomorrow
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            rescheduleDate.min = tomorrow.toISOString().split('T')[0];
            rescheduleModal.show();
        });
    }
    
    if (checkAvailabilityBtn) {
        checkAvailabilityBtn.addEventListener('click', async function() {
            const date = rescheduleDate.value;
            
            if (!date) {
                rescheduleDate.classList.add('is-invalid');
                return;
            }
            
            rescheduleDate.classList.remove('is-invalid');
            checkAvailabilityBtn.disabled = true;
            checkAvailabilityBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
            
            try {
                const response = await fetch(`/bookings/${bookingId}/available-timeslots/?date=${date}`);
                const data = await response.json();
                
                if (data.success) {
                    displayTimeslots(data.timeslots, date, data.duration);
                    document.getElementById('rescheduleStep1').style.display = 'none';
                    document.getElementById('rescheduleStep2').style.display = 'block';
                } else {
                    showAlert('danger', data.message);
                }
            } catch (error) {
                showAlert('danger', 'An error occurred while fetching available timeslots');
            } finally {
                checkAvailabilityBtn.disabled = false;
                checkAvailabilityBtn.innerHTML = '<i class="fas fa-search me-2"></i>Check Available Times';
            }
        });
    }
    
    function displayTimeslots(timeslots, date, duration) {
        const container = document.getElementById('timeslotsContainer');
        const noSlotsMsg = document.getElementById('noTimeslotsMessage');
        const selectedDateDisplay = document.getElementById('selectedDateDisplay');
        
        // Format date for display
        const dateObj = new Date(date + 'T00:00:00');
        selectedDateDisplay.textContent = dateObj.toLocaleDateString('en-US', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
        
        container.innerHTML = '';
        
        const availableSlots = timeslots.filter(slot => slot.available);
        
        if (availableSlots.length === 0) {
            noSlotsMsg.style.display = 'block';
            return;
        }
        
        noSlotsMsg.style.display = 'none';
        
        availableSlots.forEach(slot => {
            const slotBtn = document.createElement('button');
            slotBtn.type = 'button';
            slotBtn.className = 'timeslot-btn';
            
            // Format end time for display
            const endTimeObj = new Date(`2000-01-01T${slot.end_time}`);
            const displayEndTime = endTimeObj.toLocaleTimeString('en-US', { 
                hour: 'numeric', 
                minute: '2-digit',
                hour12: true 
            });
            
            slotBtn.innerHTML = `
                <div class="timeslot-time">${slot.display_time}</div>
                <div class="timeslot-separator">-</div>
                <div class="timeslot-time">${displayEndTime}</div>
                <div class="timeslot-duration">${duration} min</div>
            `;
            slotBtn.dataset.startTime = slot.start_time;
            slotBtn.dataset.endTime = slot.end_time;
            slotBtn.dataset.displayTime = slot.display_time;
            slotBtn.dataset.displayEndTime = displayEndTime;
            
            slotBtn.addEventListener('click', function() {
                // Remove active class from all slots
                document.querySelectorAll('.timeslot-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                
                // Add active class to selected slot
                this.classList.add('active');
                
                selectedSlot = {
                    date: date,
                    startTime: this.dataset.startTime,
                    endTime: this.dataset.endTime,
                    displayTime: this.dataset.displayTime,
                    displayEndTime: this.dataset.displayEndTime
                };
                
                // Show step 3 while keeping step 1 and 2 visible but disabled
                document.getElementById('rescheduleStep3').style.display = 'block';
                document.getElementById('newAppointmentTime').textContent = 
                    `${selectedDateDisplay.textContent} from ${selectedSlot.displayTime} to ${selectedSlot.displayEndTime}`;
                confirmRescheduleBtn.style.display = 'inline-block';
            });
            
            container.appendChild(slotBtn);
        });
    }
    
    if (backToDateBtn) {
        backToDateBtn.addEventListener('click', function() {
            document.getElementById('rescheduleStep2').style.display = 'none';
            document.getElementById('rescheduleStep1').style.display = 'block';
        });
    }
    
    if (backToTimeslotsBtn) {
        backToTimeslotsBtn.addEventListener('click', function() {
            document.getElementById('rescheduleStep3').style.display = 'none';
            confirmRescheduleBtn.style.display = 'none';
            // Clear selection
            document.querySelectorAll('.timeslot-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            selectedSlot = null;
        });
    }
    
    if (confirmRescheduleBtn) {
        confirmRescheduleBtn.addEventListener('click', async function() {
            const reason = rescheduleReason.value.trim();
            
            if (!reason) {
                rescheduleReason.classList.add('is-invalid');
                return;
            }
            
            if (!selectedSlot) {
                showAlert('danger', 'Please select a time slot');
                return;
            }
            
            rescheduleReason.classList.remove('is-invalid');
            confirmRescheduleBtn.disabled = true;
            confirmRescheduleBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Rescheduling...';
            
            try {
                const response = await fetch(`/bookings/${bookingId}/reschedule/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        new_date: selectedSlot.date,
                        new_start_time: selectedSlot.startTime,
                        new_end_time: selectedSlot.endTime,
                        reason: reason
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    rescheduleModal.hide();
                    showAlert('success', data.message);
                    setTimeout(() => window.location.reload(), 1500);
                } else {
                    showAlert('danger', data.message);
                    confirmRescheduleBtn.disabled = false;
                    confirmRescheduleBtn.innerHTML = '<i class="fas fa-calendar-check me-2"></i>Confirm Reschedule';
                }
            } catch (error) {
                showAlert('danger', 'An error occurred while rescheduling the booking');
                confirmRescheduleBtn.disabled = false;
                confirmRescheduleBtn.innerHTML = '<i class="fas fa-calendar-check me-2"></i>Confirm Reschedule';
            }
        });
    }
    
    // Reset modals on close
    document.getElementById('cancelBookingModal').addEventListener('hidden.bs.modal', function() {
        cancellationReason.value = '';
        cancellationReason.classList.remove('is-invalid');
    });
    
    document.getElementById('rescheduleBookingModal').addEventListener('hidden.bs.modal', function() {
        rescheduleDate.value = '';
        rescheduleReason.value = '';
        rescheduleDate.classList.remove('is-invalid');
        rescheduleReason.classList.remove('is-invalid');
        document.getElementById('rescheduleStep1').style.display = 'block';
        document.getElementById('rescheduleStep2').style.display = 'none';
        document.getElementById('rescheduleStep3').style.display = 'none';
        confirmRescheduleBtn.style.display = 'none';
        selectedSlot = null;
    });
    
    // Helper function to show alerts
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
        }, 5000);
    }
});
