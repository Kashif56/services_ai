// Leads Create JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    if (tooltipTriggerList.length > 0) {
        [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
    
    // Form validation
    const form = document.getElementById('create-lead-form');
    
    if (form) {
        // Add floating label behavior for better UX
        const formControls = form.querySelectorAll('.form-control, .form-select');
        formControls.forEach(control => {
            // Ensure labels are positioned correctly on page load if fields have values
            if (control.value !== '') {
                control.classList.add('has-value');
            }
            
            // Add focus animations
            control.addEventListener('focus', function() {
                this.parentElement.classList.add('focused');
            });
            
            control.addEventListener('blur', function() {
                this.parentElement.classList.remove('focused');
                if (this.value !== '') {
                    this.classList.add('has-value');
                } else {
                    this.classList.remove('has-value');
                }
            });
        });
        
        // Form submission validation
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Show validation messages
                form.classList.add('was-validated');
                
                // Scroll to the first invalid field with smooth animation
                const invalidField = form.querySelector(':invalid');
                if (invalidField) {
                    invalidField.focus();
                    invalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    
                    // Add shake animation to the invalid field's parent
                    const fieldContainer = invalidField.closest('.form-floating') || invalidField.parentElement;
                    fieldContainer.classList.add('shake-animation');
                    
                    // Remove animation class after it completes
                    setTimeout(() => {
                        fieldContainer.classList.remove('shake-animation');
                    }, 820); // Animation duration + small buffer
                }
                
                // Show error message
                showAlert('Please fill in all required fields.', 'danger');
            } else {
                // Add loading state to submit button
                const submitButton = form.querySelector('button[type="submit"]');
                const originalText = submitButton.innerHTML;
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Creating...';
                
                // We're not preventing default here to allow the form to submit normally
                // In a real app with AJAX submission, you would prevent default and handle submission manually
            }
        });
        
        // Phone number formatting
        const phoneInput = document.getElementById('phone');
        if (phoneInput) {
            phoneInput.addEventListener('input', function(e) {
                // Remove all non-numeric characters
                let value = e.target.value.replace(/\D/g, '');
                
                // Format the phone number as XXX-XXX-XXXX
                if (value.length > 0) {
                    if (value.length <= 3) {
                        value = value;
                    } else if (value.length <= 6) {
                        value = value.slice(0, 3) + '-' + value.slice(3);
                    } else {
                        value = value.slice(0, 3) + '-' + value.slice(3, 6) + '-' + value.slice(6, 10);
                    }
                }
                
                e.target.value = value;
            });
        }
        
        // Status and source select enhancements
        const selectFields = form.querySelectorAll('select');
        selectFields.forEach(select => {
            // Add custom styling based on selection
            select.addEventListener('change', function() {
                // Add a class based on the selected value for potential styling
                this.className = 'form-select';
                if (this.id === 'status') {
                    this.classList.add(`status-${this.value}`);
                }
                
                // Trigger a subtle animation on change
                this.classList.add('pulse-animation');
                setTimeout(() => {
                    this.classList.remove('pulse-animation');
                }, 500);
            });
        });
    }
    
    // Add animation to section icons
    const sectionIcons = document.querySelectorAll('.section-icon');
    sectionIcons.forEach(icon => {
        icon.addEventListener('mouseenter', function() {
            this.classList.add('pulse-animation');
        });
        
        icon.addEventListener('mouseleave', function() {
            this.classList.remove('pulse-animation');
        });
    });
    
    // Function to show alerts
    function showAlert(message, type = 'info') {
        const alertContainer = document.createElement('div');
        alertContainer.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
        alertContainer.setAttribute('role', 'alert');
        alertContainer.style.zIndex = '9999';
        
        alertContainer.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-${type === 'danger' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
                <div>${message}</div>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        document.body.appendChild(alertContainer);
        
        // Add entrance animation
        setTimeout(() => {
            alertContainer.classList.add('show-alert');
        }, 10);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alertContainer.classList.add('hide-alert');
            setTimeout(() => {
                const alert = bootstrap.Alert.getOrCreateInstance(alertContainer);
                alert.close();
            }, 500);
        }, 5000);
    }
    
    // Add CSS for animations
    const style = document.createElement('style');
    style.textContent = `
        .shake-animation {
            animation: shake 0.82s cubic-bezier(.36,.07,.19,.97) both;
        }
        
        .pulse-animation {
            animation: pulse 0.5s ease-in-out;
        }
        
        .show-alert {
            animation: slideIn 0.3s forwards;
        }
        
        .hide-alert {
            animation: slideOut 0.5s forwards;
        }
        
        .focused {
            border-color: #6366f1 !important;
        }
        
        @keyframes shake {
            10%, 90% { transform: translate3d(-1px, 0, 0); }
            20%, 80% { transform: translate3d(2px, 0, 0); }
            30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
            40%, 60% { transform: translate3d(4px, 0, 0); }
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        /* Status-specific styling */
        .status-new { border-left: 3px solid #3b82f6 !important; }
        .status-contacted { border-left: 3px solid #6366f1 !important; }
        .status-qualified { border-left: 3px solid #f59e0b !important; }
        .status-converted { border-left: 3px solid #10b981 !important; }
        .status-lost { border-left: 3px solid #ef4444 !important; }
    `;
    document.head.appendChild(style);
});
