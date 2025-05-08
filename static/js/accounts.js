// Account Management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Password strength validation
    const newPasswordInput = document.getElementById('new_password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    
    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', function() {
            validatePassword(this);
        });
    }
    
    if (confirmPasswordInput && newPasswordInput) {
        confirmPasswordInput.addEventListener('input', function() {
            validateConfirmPassword(this, newPasswordInput);
        });
    }
    
    // Profile form handling
    const profileForm = document.getElementById('profile-form');
    if (profileForm) {
        profileForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            // Show success message
            const alertContainer = document.getElementById('alert-container');
            if (alertContainer) {
                alertContainer.innerHTML = `
                    <div class="alert alert-success alert-dismissible fade show" role="alert">
                        <strong>Success!</strong> Your profile has been updated.
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                `;
            }
        });
    }
    
    // Settings form handling
    const settingsForm = document.getElementById('settings-form');
    if (settingsForm) {
        settingsForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            // Show success message
            const alertContainer = document.getElementById('alert-container');
            if (alertContainer) {
                alertContainer.innerHTML = `
                    <div class="alert alert-success alert-dismissible fade show" role="alert">
                        <strong>Success!</strong> Your settings have been updated.
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                `;
            }
        });
    }
    
    // Change password form handling
    const passwordForm = document.getElementById('password-form');
    if (passwordForm) {
        passwordForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            const currentPassword = document.getElementById('current_password').value;
            const newPassword = document.getElementById('new_password').value;
            const confirmPassword = document.getElementById('confirm_password').value;
            
            // Validate passwords
            if (!currentPassword || !newPassword || !confirmPassword) {
                showError('All fields are required.');
                return;
            }
            
            if (newPassword !== confirmPassword) {
                showError('New passwords do not match.');
                return;
            }
            
            // Check password strength
            if (!isStrongPassword(newPassword)) {
                return;
            }
            
            // Show success message
            const alertContainer = document.getElementById('alert-container');
            if (alertContainer) {
                alertContainer.innerHTML = `
                    <div class="alert alert-success alert-dismissible fade show" role="alert">
                        <strong>Success!</strong> Your password has been changed.
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                `;
            }
            
            // Reset form
            passwordForm.reset();
            passwordForm.classList.remove('was-validated');
        });
    }
});

// Helper functions
function validatePassword(input) {
    const password = input.value;
    let isValid = true;
    let errorMessage = '';
    
    // Check password requirements
    if (password.length < 8) {
        isValid = false;
        errorMessage = 'Password must be at least 8 characters long.';
    } else if (!/[A-Z]/.test(password)) {
        isValid = false;
        errorMessage = 'Password must contain at least one uppercase letter.';
    } else if (!/[a-z]/.test(password)) {
        isValid = false;
        errorMessage = 'Password must contain at least one lowercase letter.';
    } else if (!/[0-9]/.test(password)) {
        isValid = false;
        errorMessage = 'Password must contain at least one number.';
    } else if (!/[^A-Za-z0-9]/.test(password)) {
        isValid = false;
        errorMessage = 'Password must contain at least one special character.';
    }
    
    if (isValid) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
    } else {
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
        
        // Show error message
        const errorFeedback = input.nextElementSibling;
        if (errorFeedback && errorFeedback.classList.contains('invalid-feedback')) {
            errorFeedback.textContent = errorMessage;
        }
    }
    
    return isValid;
}

function validateConfirmPassword(input, passwordInput) {
    const confirmPassword = input.value;
    const password = passwordInput.value;
    
    if (password === confirmPassword) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        return true;
    } else {
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
        
        // Show error message
        const errorFeedback = input.nextElementSibling;
        if (errorFeedback && errorFeedback.classList.contains('invalid-feedback')) {
            errorFeedback.textContent = 'Passwords do not match.';
        }
        
        return false;
    }
}

function isStrongPassword(password) {
    if (password.length < 8) {
        showError('Password must be at least 8 characters long.');
        return false;
    }
    
    if (!/[A-Z]/.test(password)) {
        showError('Password must contain at least one uppercase letter.');
        return false;
    }
    
    if (!/[a-z]/.test(password)) {
        showError('Password must contain at least one lowercase letter.');
        return false;
    }
    
    if (!/[0-9]/.test(password)) {
        showError('Password must contain at least one number.');
        return false;
    }
    
    if (!/[^A-Za-z0-9]/.test(password)) {
        showError('Password must contain at least one special character.');
        return false;
    }
    
    return true;
}

function showError(message) {
    const alertContainer = document.getElementById('alert-container');
    if (alertContainer) {
        alertContainer.innerHTML = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <strong>Error!</strong> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
    }
}
