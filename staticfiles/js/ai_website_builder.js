// AI Website Builder JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('websiteGeneratorForm');
    const generateBtn = document.getElementById('generateBtn');
    
    if (form && generateBtn) {
        form.addEventListener('submit', function(e) {
            // Add loading state to button
            generateBtn.classList.add('loading');
            generateBtn.disabled = true;
            
            const originalText = generateBtn.innerHTML;
            generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';
            
            // Form will submit normally, but if there's an error, restore button
            setTimeout(function() {
                if (generateBtn.classList.contains('loading')) {
                    generateBtn.classList.remove('loading');
                    generateBtn.disabled = false;
                    generateBtn.innerHTML = originalText;
                }
            }, 30000); // 30 second timeout
        });
    }
    
    // Character counter for textarea
    const aiPrompt = document.getElementById('ai_prompt');
    if (aiPrompt) {
        const maxLength = 1000;
        const counter = document.createElement('div');
        counter.className = 'form-text text-end';
        counter.style.marginTop = '-0.5rem';
        counter.style.marginBottom = '1rem';
        aiPrompt.parentNode.insertBefore(counter, aiPrompt.nextSibling);
        
        function updateCounter() {
            const remaining = maxLength - aiPrompt.value.length;
            counter.textContent = `${aiPrompt.value.length} / ${maxLength} characters`;
            
            if (remaining < 100) {
                counter.style.color = '#e53e3e';
            } else if (remaining < 200) {
                counter.style.color = '#dd6b20';
            } else {
                counter.style.color = '#718096';
            }
        }
        
        aiPrompt.addEventListener('input', updateCounter);
        updateCounter();
    }
    
    // Auto-save to localStorage
    const businessNameInput = document.getElementById('business_name');
    const aiPromptInput = document.getElementById('ai_prompt');
    
    if (businessNameInput && aiPromptInput) {
        // Load saved data
        const savedBusinessName = localStorage.getItem('ai_website_business_name');
        const savedPrompt = localStorage.getItem('ai_website_prompt');
        
        if (savedBusinessName && !businessNameInput.value) {
            businessNameInput.value = savedBusinessName;
        }
        
        if (savedPrompt && !aiPromptInput.value) {
            aiPromptInput.value = savedPrompt;
        }
        
        // Save on input
        businessNameInput.addEventListener('input', function() {
            localStorage.setItem('ai_website_business_name', this.value);
        });
        
        aiPromptInput.addEventListener('input', function() {
            localStorage.setItem('ai_website_prompt', this.value);
        });
        
        // Clear on successful submit
        form.addEventListener('submit', function() {
            setTimeout(function() {
                localStorage.removeItem('ai_website_business_name');
                localStorage.removeItem('ai_website_prompt');
            }, 1000);
        });
    }
    
    // Animate feature boxes on scroll
    const featureBoxes = document.querySelectorAll('.feature-box');
    
    if (featureBoxes.length > 0) {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };
        
        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '0';
                    entry.target.style.transform = 'translateY(20px)';
                    
                    setTimeout(function() {
                        entry.target.style.transition = 'all 0.6s ease';
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                    }, 100);
                    
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);
        
        featureBoxes.forEach(function(box) {
            observer.observe(box);
        });
    }
    
    // Add tooltip to copy URL button
    const copyButtons = document.querySelectorAll('[data-copy-url]');
    copyButtons.forEach(function(btn) {
        btn.addEventListener('click', function() {
            const url = this.getAttribute('data-copy-url');
            
            navigator.clipboard.writeText(url).then(function() {
                // Show success feedback
                const originalHTML = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-check me-2"></i>Copied!';
                btn.classList.add('btn-success');
                btn.classList.remove('btn-outline-primary');
                
                setTimeout(function() {
                    btn.innerHTML = originalHTML;
                    btn.classList.remove('btn-success');
                    btn.classList.add('btn-outline-primary');
                }, 2000);
            }).catch(function(err) {
                console.error('Failed to copy:', err);
                alert('Failed to copy URL to clipboard');
            });
        });
    });
});
