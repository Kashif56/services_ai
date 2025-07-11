/**
 * License Activation Page JavaScript
 * 
 * This file contains JavaScript functionality for the license activation page.
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('License activation page loaded');
    
    // Get the license key input field
    const licenseKeyInput = document.getElementById('licence_key');
    
    if (licenseKeyInput) {
        // Format the license key as the user types (e.g., XXXX-XXXX-XXXX-XXXX)
        licenseKeyInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/[^a-zA-Z0-9]/g, '').toUpperCase();
            let formattedValue = '';
            
            for (let i = 0; i < value.length; i++) {
                if (i > 0 && i % 4 === 0 && i < 16) {
                    formattedValue += '-';
                }
                if (i < 16) {
                    formattedValue += value[i];
                }
            }
            
            e.target.value = formattedValue;
        });
    }
});
