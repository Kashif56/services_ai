// Multi-Step Form Navigation and Summary Update
(function initMultiStep() {
    // Execute immediately if DOM is already loaded, otherwise wait
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    function init() {
    let currentStep = 1;
    const totalSteps = 5;
    
    // Summary data object
    const summaryData = {
        service: null,
        servicePrice: 0,
        serviceDuration: 0,
        items: [],
        itemsPrice: 0,
        itemsDuration: 0,
        date: null,
        time: null,
        taxRate: 0.10 // 10% tax
    };
    
    // Navigation functions
    function showStep(stepNumber) {
        // Hide all steps
        document.querySelectorAll('.form-step').forEach(step => {
            step.classList.remove('active');
        });
        
        // Show current step
        const currentStepEl = document.getElementById(`step-${stepNumber}`);
        if (currentStepEl) {
            currentStepEl.classList.add('active');
        }
        
        // Update progress indicators
        document.querySelectorAll('.step').forEach((step, index) => {
            const stepNum = index + 1;
            step.classList.remove('active', 'completed');
            
            if (stepNum < stepNumber) {
                step.classList.add('completed');
            } else if (stepNum === stepNumber) {
                step.classList.add('active');
            }
        });
        
        currentStep = stepNumber;
        
        // Scroll to top of form
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    // Next step buttons
    document.querySelectorAll('.next-step').forEach(button => {
        button.addEventListener('click', function() {
            const nextStep = parseInt(this.dataset.next);
            
            // Validate current step before moving forward
            if (validateStep(currentStep)) {
                showStep(nextStep);
            }
        });
    });
    
    // Previous step buttons
    document.querySelectorAll('.prev-step').forEach(button => {
        button.addEventListener('click', function() {
            const prevStep = parseInt(this.dataset.prev);
            showStep(prevStep);
        });
    });
    
    // Click on step indicator to navigate
    document.querySelectorAll('.step').forEach(step => {
        step.addEventListener('click', function() {
            const stepNum = parseInt(this.dataset.step);
            if (stepNum <= currentStep || step.classList.contains('completed')) {
                showStep(stepNum);
            }
        });
    });
    
    // Validation function
    function validateStep(stepNumber) {
        const stepEl = document.getElementById(`step-${stepNumber}`);
        const requiredFields = stepEl.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            // Handle radio buttons differently
            if (field.type === 'radio') {
                const radioGroup = stepEl.querySelectorAll(`input[name="${field.name}"]`);
                const isAnyChecked = Array.from(radioGroup).some(radio => radio.checked);
                if (!isAnyChecked) {
                    radioGroup.forEach(radio => radio.classList.add('is-invalid'));
                    isValid = false;
                } else {
                    radioGroup.forEach(radio => radio.classList.remove('is-invalid'));
                }
            } 
            // Handle checkboxes
            else if (field.type === 'checkbox') {
                if (!field.checked) {
                    field.classList.add('is-invalid');
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            }
            // Handle all other input types
            else {
                if (!field.value || !field.value.trim()) {
                    field.classList.add('is-invalid');
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            }
        });
        
        if (!isValid) {
            alert('Please fill in all required fields before proceeding.');
        }
        
        return isValid;
    }
    
    // Update summary functions
    function updateSummary() {
        updateDateTimeSummary();
        updateDurationSummary();
        updateServiceSummary();
        updateItemsSummary();
        updatePriceSummary();
    }
    
    function updateDateTimeSummary() {
        const dateEl = document.getElementById('booking_date');
        const startTimeEl = document.getElementById('start_time');
        const endTimeEl = document.getElementById('end_time');
        const summaryEl = document.getElementById('summary-datetime');
        
        // Check if elements exist (they won't exist in edit booking page)
        if (!dateEl || !startTimeEl || !summaryEl) {
            return;
        }
        
        const date = dateEl.value;
        const startTime = startTimeEl.value;
        const endTime = endTimeEl ? endTimeEl.value : '';
        
        if (date && startTime) {
            const dateObj = new Date(date);
            const formattedDate = dateObj.toLocaleDateString('en-US', { 
                weekday: 'short', 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric' 
            });
            
            summaryEl.innerHTML = `
                <i class="fas fa-calendar text-primary me-2"></i>
                ${formattedDate}<br>
                <i class="fas fa-clock text-primary me-2"></i>
                ${formatTime(startTime)} - ${formatTime(endTime)}
            `;
            summaryData.date = date;
            summaryData.time = startTime;
        } else {
            summaryEl.innerHTML = '<i class="fas fa-calendar text-muted me-2"></i>Not selected yet';
        }
    }
    
    function updateDurationSummary() {
        const totalDuration = summaryData.serviceDuration + summaryData.itemsDuration;
        const summaryEl = document.getElementById('summary-duration');
        
        if (totalDuration > 0) {
            const hours = Math.floor(totalDuration / 60);
            const minutes = totalDuration % 60;
            let durationText = '';
            
            if (hours > 0) {
                durationText += `${hours} hour${hours > 1 ? 's' : ''}`;
            }
            if (minutes > 0) {
                if (hours > 0) durationText += ' ';
                durationText += `${minutes} min`;
            }
            
            summaryEl.innerHTML = `<i class="fas fa-clock text-primary me-2"></i>${durationText}`;
        } else {
            summaryEl.innerHTML = '<i class="fas fa-clock text-muted me-2"></i>0 minutes';
        }
    }
    
    function updateServiceSummary() {
        const summaryEl = document.getElementById('summary-service');
        
        if (summaryData.service) {
            summaryEl.innerHTML = `
                <i class="fas fa-briefcase text-primary me-2"></i>
                <strong>${summaryData.service}</strong>
            `;
        } else {
            summaryEl.innerHTML = '<i class="fas fa-briefcase text-muted me-2"></i>Not selected yet';
        }
    }
    
    function updateItemsSummary() {
        const summaryEl = document.getElementById('summary-items');
        
        if (summaryData.items.length > 0) {
            let itemsHtml = '';
            summaryData.items.forEach(item => {
                const totalItemPrice = item.price * item.quantity;
                itemsHtml += `
                    <div class="item-entry">
                        <div class="d-flex justify-content-between">
                            <span>${item.name}</span>
                            <span class="text-muted">$${totalItemPrice.toFixed(2)}</span>
                        </div>
                        ${item.quantity > 1 ? `<small class="text-muted">Qty: ${item.quantity}</small>` : ''}
                        ${item.inputValue ? `<small class="text-muted">Value: ${item.inputValue}</small>` : ''}
                    </div>
                `;
            });
            summaryEl.innerHTML = itemsHtml;
        } else {
            summaryEl.innerHTML = '<i class="fas fa-list text-muted me-2"></i>No items selected';
        }
    }
    
    function updatePriceSummary() {
        const basePrice = summaryData.servicePrice;
        const itemsPrice = summaryData.itemsPrice;
        const subtotal = basePrice + itemsPrice;
        const tax = subtotal * summaryData.taxRate;
        const grandTotal = subtotal + tax;
        
        document.getElementById('summary-base-price').textContent = `$${basePrice.toFixed(2)}`;
        document.getElementById('summary-items-price').textContent = `$${itemsPrice.toFixed(2)}`;
        document.getElementById('summary-tax').textContent = `$${tax.toFixed(2)}`;
        document.getElementById('summary-grand-total').textContent = `$${grandTotal.toFixed(2)}`;
    }
    
    // Helper function to format time
    function formatTime(timeString) {
        if (!timeString) return '';
        const [hours, minutes] = timeString.split(':');
        const hour = parseInt(hours);
        const ampm = hour >= 12 ? 'PM' : 'AM';
        const displayHour = hour % 12 || 12;
        return `${displayHour}:${minutes} ${ampm}`;
    }
    
    // Event listeners for form fields
    
    // Service selection - handle both select dropdown and radio buttons
    const serviceSelect = document.getElementById('service_type');
    if (serviceSelect) {
        serviceSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            if (this.value) {
                summaryData.service = selectedOption.dataset.name;
                summaryData.servicePrice = parseFloat(selectedOption.dataset.price) || 0;
                summaryData.serviceDuration = parseInt(selectedOption.dataset.duration) || 0;
            } else {
                summaryData.service = null;
                summaryData.servicePrice = 0;
                summaryData.serviceDuration = 0;
            }
            updateSummary();
        });
    }
    
    // Handle radio button service selection (for multi-step form)
    const serviceRadios = document.querySelectorAll('input[name="service_type"]');
    if (serviceRadios.length > 0) {
        serviceRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                if (this.checked) {
                    summaryData.service = this.dataset.name;
                    summaryData.servicePrice = parseFloat(this.dataset.price) || 0;
                    summaryData.serviceDuration = parseInt(this.dataset.duration) || 0;
                    updateSummary();
                }
            });
        });
    }
    
    // Date and time fields
    const dateField = document.getElementById('booking_date');
    const startTimeField = document.getElementById('start_time');
    const endTimeField = document.getElementById('end_time');
    
    if (dateField) {
        dateField.addEventListener('change', updateSummary);
    }
    if (startTimeField) {
        startTimeField.addEventListener('change', updateSummary);
    }
    if (endTimeField) {
        endTimeField.addEventListener('change', updateSummary);
    }
    
    // Service items handling (will be integrated with existing service items logic)
    window.updateServiceItemsSummary = function(items) {
        console.log('=== UPDATE SERVICE ITEMS SUMMARY ===');
        console.log('Items to update:', items);
        console.log('Previous items:', summaryData.items);
        
        summaryData.items = items;
        summaryData.itemsPrice = items.reduce((total, item) => total + (item.price * item.quantity), 0);
        summaryData.itemsDuration = items.reduce((total, item) => total + (item.duration * item.quantity), 0);
        
        console.log('New items price:', summaryData.itemsPrice);
        console.log('New items duration:', summaryData.itemsDuration);
        
        updateSummary();
    };
    
    // Listen for service item changes from the main booking script
    // This function will be called when service items are selected/deselected
    document.addEventListener('serviceItemsUpdated', function(event) {
        const items = event.detail.items || {};
        const itemsArray = [];
        
        console.log('=== SERVICE ITEMS UPDATED EVENT ===');
        console.log('Items received:', items);
        console.log('Items count:', Object.keys(items).length);
        
        // Convert the items object to array format for summary
        Object.values(items).forEach(item => {
            itemsArray.push({
                name: item.name,
                price: item.price,
                quantity: item.quantity,
                duration: item.duration || 0,
                inputValue: item.inputValue || null  // Include user input value
            });
        });
        
        console.log('Items array for summary:', itemsArray);
        console.log('Items array length:', itemsArray.length);
        
        updateServiceItemsSummary(itemsArray);
    });
    
    // Initialize summary
    updateSummary();
    
    // Set minimum date to today
    if (dateField) {
        const today = new Date().toISOString().split('T')[0];
        dateField.setAttribute('min', today);
    }
    
    // Expose showStep function globally for use in booking submission
    window.showStep = showStep;
    }
})();
