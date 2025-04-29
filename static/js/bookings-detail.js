// bookings-detail.js - Enhance the booking detail page

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Print functionality
    const printButton = document.querySelector('.print-booking');
    if (printButton) {
        printButton.addEventListener('click', function(e) {
            e.preventDefault();
            window.print();
        });
    }
    
    // Confirmation dialogs for status changes
    const confirmButtons = document.querySelectorAll('.confirm-booking');
    if (confirmButtons) {
        confirmButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                if (!confirm('Are you sure you want to confirm this booking?')) {
                    e.preventDefault();
                }
            });
        });
    }
    
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
    
    const completeButtons = document.querySelectorAll('.complete-booking');
    if (completeButtons) {
        completeButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                if (!confirm('Are you sure you want to mark this booking as completed?')) {
                    e.preventDefault();
                }
            });
        });
    }
    
    const noShowButtons = document.querySelectorAll('.no-show-booking');
    if (noShowButtons) {
        noShowButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                if (!confirm('Are you sure you want to mark this booking as no-show?')) {
                    e.preventDefault();
                }
            });
        });
    }
    
    // Update the links in the booking index to point to the detail page
    const updateIndexLinks = () => {
        if (window.opener && window.opener.document) {
            try {
                const viewLinks = window.opener.document.querySelectorAll('.view-booking-link');
                viewLinks.forEach(link => {
                    link.href = window.location.href;
                });
            } catch (e) {
                console.error('Error updating opener links:', e);
            }
        }
    };
    
    // Try to update links if this page was opened from the index
    updateIndexLinks();
});
