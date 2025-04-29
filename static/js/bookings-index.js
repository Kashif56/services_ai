// bookings-index.js - Enhance the bookings index page

document.addEventListener('DOMContentLoaded', function() {
    // Auto-submit form when status or date filters change
    const filterForm = document.getElementById('booking-filter-form');
    if (filterForm) {
        const statusSelect = document.getElementById('status');
        const dateFromInput = document.getElementById('date_from');
        const dateToInput = document.getElementById('date_to');
        
        // Auto-submit when status changes
        if (statusSelect) {
            statusSelect.addEventListener('change', function() {
                filterForm.submit();
            });
        }
        
        // Initialize date range validation
        if (dateFromInput && dateToInput) {
            dateFromInput.addEventListener('change', function() {
                if (dateToInput.value && this.value > dateToInput.value) {
                    dateToInput.value = this.value;
                }
            });
            
            dateToInput.addEventListener('change', function() {
                if (dateFromInput.value && this.value < dateFromInput.value) {
                    dateFromInput.value = this.value;
                }
            });
        }
    }
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Confirm booking cancellation
    const cancelButtons = document.querySelectorAll('.cancel-booking');
    if (cancelButtons) {
        cancelButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                if (!confirm('Are you sure you want to cancel this booking?')) {
                    e.preventDefault();
                }
            });
        });
    }
    
    // Highlight today's bookings
    const today = new Date().toISOString().split('T')[0];
    document.querySelectorAll('tr[data-date]').forEach(row => {
        if (row.dataset.date === today) {
            row.classList.add('table-primary', 'today-booking');
        }
    });
});
