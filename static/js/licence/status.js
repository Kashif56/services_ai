/**
 * License Status Page JavaScript
 * 
 * This file contains JavaScript functionality for the license status page.
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('License status page loaded');
    
    // Add copy functionality for license keys
    const licenseKeys = document.querySelectorAll('code');
    
    licenseKeys.forEach(key => {
        key.style.cursor = 'pointer';
        key.title = 'Click to copy';
        
        key.addEventListener('click', function() {
            const textToCopy = this.textContent;
            
            // Create a temporary textarea element to copy text
            const textarea = document.createElement('textarea');
            textarea.value = textToCopy;
            textarea.setAttribute('readonly', '');
            textarea.style.position = 'absolute';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            
            // Select and copy the text
            textarea.select();
            document.execCommand('copy');
            
            // Remove the temporary textarea
            document.body.removeChild(textarea);
            
            // Show feedback
            const originalText = this.textContent;
            this.textContent = 'Copied!';
            
            // Reset after a short delay
            setTimeout(() => {
                this.textContent = originalText;
            }, 1500);
        });
    });
});
