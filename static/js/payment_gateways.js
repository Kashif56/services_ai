document.addEventListener('DOMContentLoaded', function() {
    // Set default payment gateway
    const setDefaultButtons = document.querySelectorAll('[id^="set"][id$="DefaultBtn"]');
    
    setDefaultButtons.forEach(button => {
        button.addEventListener('click', function() {
            const gateway = this.dataset.gateway;
            setDefaultPaymentGateway(gateway);
        });
    });

    // Form submission handling
    const stripeForm = document.getElementById('stripeForm');
    const squareForm = document.getElementById('squareForm');
    
    if (stripeForm) {
        stripeForm.addEventListener('submit', function(e) {
            e.preventDefault();
            submitForm(this, 'Stripe credentials saved successfully!');
        });
    }
    
    if (squareForm) {
        squareForm.addEventListener('submit', function(e) {
            e.preventDefault();
            submitForm(this, 'Square credentials saved successfully!');
        });
    }
});

function setDefaultPaymentGateway(gateway) {
    fetch('/business/payment-gateways/set-default/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ gateway: gateway })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            showToast('success', data.message);
            // Reload page to reflect changes
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showToast('danger', data.message || 'An error occurred');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('danger', 'An error occurred while setting the default payment gateway');
    });
}

function submitForm(form, successMessage) {
    const formData = new FormData(form);
    
    fetch(form.action, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close modal
            const modalElement = form.closest('.modal');
            const modal = bootstrap.Modal.getInstance(modalElement);
            modal.hide();
            
            // Show success message
            showToast('success', data.message || successMessage);
            
            // Reload page to reflect changes
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showToast('danger', data.message || 'An error occurred');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('danger', 'An error occurred while saving the credentials');
    });
}

function getCsrfToken() {
    return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
}

function showToast(type, message) {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    // Add toast to container
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Initialize and show toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 5000 });
    toast.show();
    
    // Remove toast after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}
