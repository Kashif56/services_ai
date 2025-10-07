// Staff Accounts Management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize event listeners
    initializeEventListeners();

    // View Toggle
    const listViewBtn = document.getElementById('listViewBtn');
    const cardViewBtn = document.getElementById('cardViewBtn');
    const listView = document.getElementById('listView');
    const cardView = document.getElementById('cardView');

    if (listViewBtn && cardViewBtn) {
        listViewBtn.addEventListener('click', function() {
            listView.classList.remove('d-none');
            cardView.classList.add('d-none');
            listViewBtn.classList.add('active');
            cardViewBtn.classList.remove('active');
            localStorage.setItem('staffAccountsView', 'list');
            // Re-initialize event listeners after view change
            initializeEventListeners();
        });

        cardViewBtn.addEventListener('click', function() {
            cardView.classList.remove('d-none');
            listView.classList.add('d-none');
            cardViewBtn.classList.add('active');
            listViewBtn.classList.remove('active');
            localStorage.setItem('staffAccountsView', 'card');
            // Re-initialize event listeners after view change
            initializeEventListeners();
        });

        // Restore saved view preference
        const savedView = localStorage.getItem('staffAccountsView');
        if (savedView === 'list') {
            listViewBtn.click();
        }
    }
});

// Function to initialize all event listeners
function initializeEventListeners() {
    // Create Account Modal
    const createAccountModal = new bootstrap.Modal(document.getElementById('createAccountModal'));
    const createAccountForm = document.getElementById('createAccountForm');
    const confirmCreateAccountBtn = document.getElementById('confirmCreateAccount');

    // Remove old event listeners by cloning buttons (prevents duplicate listeners)
    document.querySelectorAll('.create-account-btn').forEach(btn => {
        const newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);
    });

    // Attach create account event listeners
    document.querySelectorAll('.create-account-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const staffId = this.dataset.staffId;
            const staffName = this.dataset.staffName;
            const staffEmail = this.dataset.staffEmail;

            document.getElementById('createStaffId').value = staffId;
            document.getElementById('createStaffName').textContent = staffName;
            
            // Auto-generate username suggestion from email
            const suggestedUsername = staffEmail.split('@')[0].toLowerCase().replace(/[^a-z0-9]/g, '');
            document.getElementById('createUsername').value = suggestedUsername;
            
            // Clear password fields
            document.getElementById('createPassword').value = '';
            document.getElementById('createConfirmPassword').value = '';

            createAccountModal.show();
        });
    });

    if (confirmCreateAccountBtn) {
        confirmCreateAccountBtn.addEventListener('click', function() {
            if (!createAccountForm.checkValidity()) {
                createAccountForm.reportValidity();
                return;
            }

            const staffId = document.getElementById('createStaffId').value;
            const username = document.getElementById('createUsername').value;
            const password = document.getElementById('createPassword').value;
            const confirmPassword = document.getElementById('createConfirmPassword').value;

            // Validate passwords match
            if (password !== confirmPassword) {
                showAlert('Passwords do not match!', 'danger');
                return;
            }

            // Validate password length
            if (password.length < 8) {
                showAlert('Password must be at least 8 characters long!', 'danger');
                return;
            }

            // Disable button and show loading
            confirmCreateAccountBtn.disabled = true;
            confirmCreateAccountBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Creating...';

            // Send AJAX request
            fetch('/business/staff-accounts/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    staff_id: staffId,
                    username: username,
                    password: password,
                    confirm_password: confirmPassword
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert(data.message, 'success');
                    createAccountModal.hide();
                    // Reload page after short delay
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    showAlert(data.message, 'danger');
                    confirmCreateAccountBtn.disabled = false;
                    confirmCreateAccountBtn.innerHTML = '<i class="fas fa-plus-circle me-1"></i>Create Account';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('An error occurred while creating the account.', 'danger');
                confirmCreateAccountBtn.disabled = false;
                confirmCreateAccountBtn.innerHTML = '<i class="fas fa-plus-circle me-1"></i>Create Account';
            });
        });
    }

    // Remove old event listeners for delete buttons
    document.querySelectorAll('.delete-account-btn').forEach(btn => {
        const newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);
    });

    // Delete Account
    document.querySelectorAll('.delete-account-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const staffId = this.dataset.staffId;
            const staffName = this.dataset.staffName;

            if (!confirm(`Are you sure you want to delete the account for ${staffName}?\n\nThis action cannot be undone. The staff member will no longer be able to login.`)) {
                return;
            }

            // Disable button and show loading
            this.disabled = true;
            const originalHTML = this.innerHTML;
            this.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

            // Send AJAX request
            fetch('/business/staff-accounts/delete/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    staff_id: staffId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert(data.message, 'success');
                    // Reload page after short delay
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    showAlert(data.message, 'danger');
                    this.disabled = false;
                    this.innerHTML = originalHTML;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('An error occurred while deleting the account.', 'danger');
                this.disabled = false;
                this.innerHTML = originalHTML;
            });
        });
    });

    // Remove old event listeners for toggle buttons
    document.querySelectorAll('.toggle-status-btn').forEach(btn => {
        const newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);
    });

    // Toggle Account Status
    document.querySelectorAll('.toggle-status-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const staffId = this.dataset.staffId;
            const staffName = this.dataset.staffName;
            const isActive = this.dataset.isActive === 'true';
            const newStatus = !isActive;

            const action = newStatus ? 'activate' : 'deactivate';
            if (!confirm(`Are you sure you want to ${action} the account for ${staffName}?`)) {
                return;
            }

            // Disable button and show loading
            this.disabled = true;
            const originalHTML = this.innerHTML;
            this.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

            // Send AJAX request
            fetch('/business/staff-accounts/toggle-status/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    staff_id: staffId,
                    is_active: newStatus
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert(data.message, 'success');
                    // Reload page after short delay
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    showAlert(data.message, 'danger');
                    this.disabled = false;
                    this.innerHTML = originalHTML;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('An error occurred while updating the account status.', 'danger');
                this.disabled = false;
                this.innerHTML = originalHTML;
            });
        });
    });

    // Reset Password Modal
    const resetPasswordModal = new bootstrap.Modal(document.getElementById('resetPasswordModal'));
    const resetPasswordForm = document.getElementById('resetPasswordForm');
    const confirmResetPasswordBtn = document.getElementById('confirmResetPassword');

    // Remove old event listeners for reset password buttons
    document.querySelectorAll('.reset-password-btn').forEach(btn => {
        const newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);
    });

    document.querySelectorAll('.reset-password-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const staffId = this.dataset.staffId;
            const staffName = this.dataset.staffName;

            document.getElementById('resetStaffId').value = staffId;
            document.getElementById('resetStaffName').textContent = staffName;
            
            // Clear password fields
            document.getElementById('newPassword').value = '';
            document.getElementById('confirmNewPassword').value = '';

            resetPasswordModal.show();
        });
    });

    if (confirmResetPasswordBtn) {
        confirmResetPasswordBtn.addEventListener('click', function() {
            if (!resetPasswordForm.checkValidity()) {
                resetPasswordForm.reportValidity();
                return;
            }

            const staffId = document.getElementById('resetStaffId').value;
            const newPassword = document.getElementById('newPassword').value;
            const confirmPassword = document.getElementById('confirmNewPassword').value;

            // Validate passwords match
            if (newPassword !== confirmPassword) {
                showAlert('Passwords do not match!', 'danger');
                return;
            }

            // Validate password length
            if (newPassword.length < 8) {
                showAlert('Password must be at least 8 characters long!', 'danger');
                return;
            }

            // Disable button and show loading
            confirmResetPasswordBtn.disabled = true;
            confirmResetPasswordBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Resetting...';

            // Send AJAX request
            fetch('/business/staff-accounts/reset-password/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    staff_id: staffId,
                    new_password: newPassword,
                    confirm_password: confirmPassword
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert(data.message, 'success');
                    resetPasswordModal.hide();
                    confirmResetPasswordBtn.disabled = false;
                    confirmResetPasswordBtn.innerHTML = '<i class="fas fa-key me-1"></i>Reset Password';
                } else {
                    showAlert(data.message, 'danger');
                    confirmResetPasswordBtn.disabled = false;
                    confirmResetPasswordBtn.innerHTML = '<i class="fas fa-key me-1"></i>Reset Password';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('An error occurred while resetting the password.', 'danger');
                confirmResetPasswordBtn.disabled = false;
                confirmResetPasswordBtn.innerHTML = '<i class="fas fa-key me-1"></i>Reset Password';
            });
        });
    }
}

// Helper function to show alerts
function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.style.minWidth = '300px';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
