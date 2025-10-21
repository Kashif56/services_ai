// booking-widget-core.js - Widget version of booking form with dynamic fields and pricing

(function initWidgetCore() {
    // Execute immediately if DOM is already loaded, otherwise wait
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    function init() {
    const form = document.getElementById('widget-booking-form');
    if (!form) return;

    // Cache DOM elements (with null checks for multi-step form)
    const serviceTypeSelect = document.getElementById('service_type');
    const serviceDetailsDiv = document.getElementById('service-details');
    const serviceDurationSpan = document.getElementById('service-duration');
    const servicePriceSpan = document.getElementById('service-price');
    const serviceItemsSection = document.getElementById('service-items-section');
    const serviceItemsContainer = document.getElementById('service-items-container');
    // We're not using industry fields container as requested
    const bookingSummary = document.getElementById('booking-summary');
    const summaryService = document.getElementById('summary-service');
    const summaryDateTime = document.getElementById('summary-datetime');
    const summaryLocation = document.getElementById('summary-location');
    const summaryDuration = document.getElementById('summary-duration');
    const totalPriceSpan = document.getElementById('total-price');
    const startTimeInput = document.getElementById('start_time');
    const endTimeInput = document.getElementById('end_time');
    const bookingDateInput = document.getElementById('booking_date');
    const locationTypeSelect = document.getElementById('location_type');
    const locationDetailsInput = document.getElementById('location_details');
    // Staff selection elements
    const staffMemberSelect = document.getElementById('staff_member_id');
    const staffAvailabilityMessage = document.getElementById('staff-availability-message');
    const alternateTimeslotsContainer = document.getElementById('alternate-timeslots-container');
    const alternateTimeslots = document.getElementById('alternate-timeslots');
    
    // Check if we're using the multi-step form (new template)
    const isMultiStepForm = document.querySelector('.steps-progress') !== null;

    // State variables
    let selectedServiceId = null;
    let basePrice = 0;
    let baseDuration = 0;
    let serviceItems = [];
    let selectedItems = {};
    let totalPrice = 0;
    let totalDuration = 0;
    let availabilityCheckTimeout = null;

    // Service selection change handler
    // Handle both select dropdown (old) and radio buttons (new)
    if (serviceTypeSelect) {
        // Check if it's a select element or radio buttons
        if (serviceTypeSelect.tagName === 'SELECT') {
            serviceTypeSelect.addEventListener('change', handleServiceChange);
        }
    }
    
    // Handle radio button service selection
    const serviceRadios = document.querySelectorAll('input[name="service_type"]');
    if (serviceRadios.length > 0) {
        serviceRadios.forEach(radio => {
            radio.addEventListener('change', handleServiceChange);
        });
    }
    
    function handleServiceChange(event) {
        const target = event.target;
        let serviceId, duration, price;
        
        if (target.tagName === 'SELECT') {
            // Handle select dropdown
            serviceId = target.value;
            if (serviceId) {
                const selectedOption = target.options[target.selectedIndex];
                duration = selectedOption.dataset.duration;
                price = selectedOption.dataset.price;
            }
        } else if (target.type === 'radio') {
            // Handle radio button
            serviceId = target.value;
            duration = target.dataset.duration;
            price = target.dataset.price;
        }
        
        selectedServiceId = serviceId;
        
        if (serviceId) {
            basePrice = parseFloat(price);
            
            // Update service details (only if elements exist - old template)
            if (serviceDurationSpan) serviceDurationSpan.textContent = duration;
            if (servicePriceSpan) servicePriceSpan.textContent = price;
            if (serviceDetailsDiv) serviceDetailsDiv.classList.remove('d-none');
            
            // Store base duration
            baseDuration = parseInt(duration);
            totalDuration = baseDuration;
            
            // Clear selected items when service changes
            console.log('=== SERVICE CHANGE ===');
            console.log('New Service ID:', serviceId);
            console.log('Clearing selected items. Previous items:', Object.keys(selectedItems).length);
            selectedItems = {};
            console.log('Selected items cleared');
            
            // Immediately update the summary with cleared items
            updateTotalPrice();
            
            // Calculate end time based on start time and duration
            if (startTimeInput.value) {
                calculateEndTime(startTimeInput.value, totalDuration);
            }
            
            // Fetch service items
            fetchServiceItems(serviceId);
            
            // Not fetching industry fields as requested
            
            // Update summary
            updateBookingSummary();
            
            // Check staff availability if date and time are set
            if (bookingDateInput.value && startTimeInput.value && endTimeInput.value) {
                checkStaffAvailability();
            }
        } else {
            if (serviceDetailsDiv) serviceDetailsDiv.classList.add('d-none');
            // Service items section remains visible, just update content
            if (serviceItemsContainer) {
                serviceItemsContainer.innerHTML = '<div class="alert alert-info">Please select a service to view available items</div>';
            }
            if (bookingSummary) bookingSummary.classList.add('d-none');
            basePrice = 0;
            totalPrice = 0;
            selectedItems = {};
            updateTotalPrice();
            
            // Reset staff selection
            resetStaffSelection();
        }
    }

    // Date and time change handlers
    if (bookingDateInput && startTimeInput) {
        bookingDateInput.addEventListener('change', function() {
            updateBookingSummary();
            // Check staff availability when date changes
            if (selectedServiceId && startTimeInput.value && endTimeInput.value) {
                checkStaffAvailability();
            }
        });
        
        startTimeInput.addEventListener('change', function() {
            updateBookingSummary();
            
            // Calculate end time when start time changes
            if (selectedServiceId) {
                calculateEndTime(this.value, totalDuration);
            }
            
            // Check staff availability when start time changes
            if (selectedServiceId && bookingDateInput.value) {
                checkStaffAvailability();
            }
        });
        
        endTimeInput.addEventListener('change', function() {
            updateBookingSummary();
            
            // Check staff availability when end time changes
            if (selectedServiceId && bookingDateInput.value && startTimeInput.value) {
                checkStaffAvailability();
            }
        });
    }

    // Location change handlers
    if (locationTypeSelect) {
        locationTypeSelect.addEventListener('change', function() {
            updateBookingSummary();
            
            // Show/hide location details based on selection
            if (this.value === 'onsite' || this.value === 'virtual') {
                locationDetailsInput.closest('.mb-3').classList.remove('d-none');
                if (this.value === 'onsite') {
                    locationDetailsInput.placeholder = 'Enter client address';
                } else {
                    locationDetailsInput.placeholder = 'Enter meeting link or details';
                }
            } else {
                locationDetailsInput.closest('.mb-3').classList.add('d-none');
            }
        });
        
        locationDetailsInput.addEventListener('change', updateBookingSummary);
    }

    // Calculate end time based on start time and duration
    function calculateEndTime(startTime, durationMinutes) {
        if (!startTime || !durationMinutes) return;
        
        const [hours, minutes] = startTime.split(':').map(Number);
        const startDate = new Date();
        startDate.setHours(hours, minutes, 0, 0);
        
        const endDate = new Date(startDate.getTime() + durationMinutes * 60000);
        const endHours = endDate.getHours().toString().padStart(2, '0');
        const endMinutes = endDate.getMinutes().toString().padStart(2, '0');
        
        endTimeInput.value = `${endHours}:${endMinutes}`;
    }

    // Fetch service items for the selected service
    function fetchServiceItems(serviceId) {
        // In a real implementation, this would be an AJAX call to the server
        // For now, we'll simulate with a timeout
        serviceItemsContainer.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
        // Service items section is always visible now
        
        // Make the actual API call to the widget endpoint
        const widgetState = window.BookingWidget;
        fetch(`${widgetState.apiBaseUrl}/bookings/widget/${widgetState.businessId}/service-items/${serviceId}/`)
            .then(response => response.json())
            .then(data => {
                serviceItems = data.items || [];
                renderServiceItems(serviceItems);
            })
            .catch(error => {
                console.error('Error fetching service items:', error);
                serviceItemsContainer.innerHTML = '<div class="alert alert-danger">Error loading service items</div>';
            });
    }

    // Check staff availability based on selected date, time, and service
    function checkStaffAvailability() {
        // Clear any pending timeout
        if (availabilityCheckTimeout) {
            clearTimeout(availabilityCheckTimeout);
        }
        
        // Set a short timeout to prevent too many API calls when user is still making changes
        availabilityCheckTimeout = setTimeout(() => {
            // Reset staff selection
            resetStaffSelection();
            
            // Show loading indicator
            staffAvailabilityMessage.innerHTML = '<div class="spinner-border spinner-border-sm text-primary" role="status"><span class="visually-hidden">Loading...</span></div> Checking staff availability...';
            
            // Get the selected date, time, and service
            const date = bookingDateInput.value;
            const startTime = startTimeInput.value;
            const endTime = endTimeInput.value;
            
            if (!date || !startTime || !endTime || !selectedServiceId) {
                staffAvailabilityMessage.textContent = 'Please select date, time, and service to check staff availability.';
                return;
            }
            
            // Use the total duration (service + items) instead of just service duration
            const duration = totalDuration || 60; // Use totalDuration which includes service items
            
            // Make API call to check availability
            const widgetState = window.BookingWidget;
            const url = `${widgetState.apiBaseUrl}/bookings/widget/${widgetState.businessId}/check-availability/?date=${date}&time=${startTime}&duration_minutes=${duration}&service_offering_id=${selectedServiceId}`;
            
            console.log("Checking availability with URL:", url);
            
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.is_available) {
                        // Staff is available, populate the dropdown
                        populateStaffDropdown(data.available_staff);
                        staffAvailabilityMessage.innerHTML = '<span class="text-success"><i class="fas fa-check-circle"></i> Staff available for this time slot</span>';
                        alternateTimeslotsContainer.classList.add('d-none');
                    } else {
                        // No staff available, show alternate timeslots
                        staffAvailabilityMessage.innerHTML = `<span class="text-danger"><i class="fas fa-exclamation-circle"></i> ${data.reason}</span>`;
                        
                        if (data.alternate_slots && data.alternate_slots.length > 0) {
                            renderAlternateTimeslots(data.alternate_slots);
                            alternateTimeslotsContainer.classList.remove('d-none');
                        } else {
                            alternateTimeslotsContainer.classList.add('d-none');
                        }
                    }
                })
                .catch(error => {
                    console.error('Error checking staff availability:', error);
                    staffAvailabilityMessage.innerHTML = '<span class="text-danger"><i class="fas fa-exclamation-circle"></i> Error checking staff availability</span>';
                });
        }, 500); // 500ms delay
    }
    
    // Reset staff selection
    function resetStaffSelection() {
        // Clear staff dropdown
        while (staffMemberSelect.options.length > 1) {
            staffMemberSelect.remove(1);
        }
        staffMemberSelect.value = '';
        staffAvailabilityMessage.textContent = '';
        alternateTimeslotsContainer.classList.add('d-none');
    }
    
    // Populate staff dropdown with available staff
    function populateStaffDropdown(staffList) {
        // Clear existing options except the default one
        while (staffMemberSelect.options.length > 1) {
            staffMemberSelect.remove(1);
        }
        
        if (staffList && staffList.length > 0) {
            staffList.forEach(staff => {
                const option = document.createElement('option');
                option.value = staff.id;
                option.textContent = staff.name;
                staffMemberSelect.appendChild(option);
            });
            
            // Select the first staff member by default
            if (staffMemberSelect.options.length > 1) {
                staffMemberSelect.selectedIndex = 1;
            }
        }
    }
    
    // Render alternate timeslots
    function renderAlternateTimeslots(slots) {
        if (!slots || slots.length === 0) {
            alternateTimeslots.innerHTML = '<div class="alert alert-info">No alternate timeslots available</div>';
            return;
        }
        
        let html = '<div class="list-group">';
        slots.forEach(slot => {
            const date = new Date(slot.date).toLocaleDateString();
            const startTime = formatTime(slot.time);
            const endTime = formatTime(slot.end_time);
            
            html += `
                <button type="button" class="list-group-item list-group-item-action alternate-slot" 
                    data-date="${slot.date}" 
                    data-time="${slot.time}" 
                    data-end-time="${slot.end_time}"
                    data-staff-id="${slot.staff.id}"
                    data-staff-name="${slot.staff.name}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <i class="far fa-calendar-alt me-2"></i> ${date}, ${startTime} - ${endTime}
                        </div>
                        <div>
                            <span class="badge bg-info text-dark">Staff: ${slot.staff.name}</span>
                        </div>
                    </div>
                </button>
            `;
        });
        html += '</div>';
        
        alternateTimeslots.innerHTML = html;
        
        // Add event listeners to alternate timeslot buttons
        document.querySelectorAll('.alternate-slot').forEach(button => {
            button.addEventListener('click', function() {
                // Update form with selected timeslot
                bookingDateInput.value = this.dataset.date;
                startTimeInput.value = this.dataset.time;
                endTimeInput.value = this.dataset.endTime;
                
                // Update staff selection
                populateStaffDropdown([{
                    id: this.dataset.staffId,
                    name: this.dataset.staffName
                }]);
                
                // Update availability message
                staffAvailabilityMessage.innerHTML = '<span class="text-success"><i class="fas fa-check-circle"></i> Staff available for this time slot</span>';
                
                // Hide alternate timeslots
                alternateTimeslotsContainer.classList.add('d-none');
                
                // Update booking summary
                updateBookingSummary();
            });
        });
    }

    // Render service items in the container
    function renderServiceItems(items) {
        if (!items || items.length === 0) {
            serviceItemsContainer.innerHTML = '<div class="alert alert-info">No additional service items available</div>';
            return;
        }
        
        let html = '<div class="row">';
        items.forEach(item => {
            // Determine if this is a free item or not
            const isFreeItem = item.price_type === 'free';
            
            // Determine if this item should show quantity controls
            // 1. Don't show quantity for text input types (text, textarea, select, boolean) when free
            // 2. Don't show quantity for number field type when NOT free (as the number input itself serves as the quantity)
            const shouldShowQuantity = item.max_quantity > 1 && 
                                      !((item.price_type === 'free' && ['text', 'textarea', 'select', 'boolean'].includes(item.field_type)) || 
                                        (item.price_type !== 'free' && item.field_type === 'number'));
            
            html += `
                <div class="col-md-6 mb-3">
                    <div class="service-item-card-wrapper">
                        <input class="service-item-checkbox-input" 
                               type="checkbox" 
                               id="item_${item.id}" 
                               name="service_items[]" 
                               value="${item.id}"
                               data-price="${item.price_value}"
                               data-duration="${item.duration_minutes || 0}"
                               data-field-type="${item.field_type}"
                               data-price-type="${item.price_type}"
                               data-required="${!item.is_optional}"
                               ${item.is_optional ? '' : 'checked'}>
                        <label class="service-item-card ${item.is_optional ? '' : 'service-item-required'}" for="item_${item.id}">
                            <div class="service-item-header">
                                <div class="service-item-check-icon">
                                    <i class="fas fa-check"></i>
                                </div>
                                <div class="service-item-info">
                                    <h5 class="service-item-title">${item.name}</h5>
                                    <span class="service-item-badge ${item.is_optional ? 'badge-optional' : 'badge-required'}">
                                        ${item.is_optional ? 'Optional' : 'Required'}
                                    </span>
                                </div>
                            </div>
                            
                            ${item.description ? `<p class="service-item-description">${item.description}</p>` : ''}
                            
                            <div class="service-item-pricing">
                                <span class="service-item-price">${item.price_type !== 'free' ? '$' + item.price_value : 'Free'}</span>
                                ${parseInt(item.duration_minutes) > 0 ? `<span class="service-item-duration"><i class="fas fa-clock me-1"></i>+${item.duration_minutes} min</span>` : ''}
                            </div>
                        </label>
                        
                        <!-- Field input based on field_type and price_type -->
                        <div class="mt-3 item-field-container ${item.is_optional ? 'd-none' : ''}" id="field_container_${item.id}">
                            ${renderItemField(item)}
                        </div>
                        
                        ${shouldShowQuantity ? `
                        <div class="quantity-control ${item.is_optional && !selectedItems[item.id] ? 'd-none' : ''}">
                            <label for="quantity_${item.id}">Quantity:</label>
                            <div class="input-group input-group-sm">
                                <button type="button" class="btn btn-outline-secondary decrease-qty" data-item-id="${item.id}">-</button>
                                <input type="number" class="form-control text-center item-quantity" 
                                       id="quantity_${item.id}" 
                                       name="item_quantity_${item.id}" 
                                       min="1" 
                                       default="1"
                                       max="${item.max_quantity}" 
                                       value="${selectedItems[item.id]?.quantity || 1}">
                                <button type="button" class="btn btn-outline-secondary increase-qty" data-item-id="${item.id}">+</button>
                            </div>
                        </div>
                        ` : ''}
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        serviceItemsContainer.innerHTML = html;
        
        // Helper function to render the appropriate field based on field_type and price_type
        function renderItemField(item) {
            // For number field type with paid pricing
            if (item.field_type === 'number' && item.price_type === 'paid') {
                return `
                    <div class="form-group">
                        <label for="field_${item.id}">Quantity: <span class="text-muted small">(Max: ${item.max_quantity})</span></label>
                        <input type="number" 
                               class="form-control item-number-input" 
                               id="field_${item.id}" 
                               name="item_field_${item.id}" 
                               data-item-id="${item.id}"
                               placeholder="Enter quantity"
                               min="1"
                               max="${item.max_quantity}"
                               value="1">
                    </div>
                `;
            }
            
            // For boolean field type with option pricing
            if (item.field_type === 'boolean' && item.option_pricing) {
                const yesConfig = item.option_pricing.yes || { price_type: 'free', price_value: 0 };
                const noConfig = item.option_pricing.no || { price_type: 'free', price_value: 0 };
                
                return `
                    <div class="form-group">
                        <label>Select an option:</label>
                        <div class="form-check">
                            <input type="radio" 
                                   class="form-check-input item-boolean-input" 
                                   id="field_${item.id}_yes" 
                                   name="item_field_${item.id}" 
                                   value="yes"
                                   data-item-id="${item.id}"
                                   data-price-type="${yesConfig.price_type}"
                                   data-price-value="${yesConfig.price_value}">
                            <label class="form-check-label" for="field_${item.id}_yes">
                                Yes ${yesConfig.price_type === 'paid' ? '<span class="text-success">($' + yesConfig.price_value + ')</span>' : '<span class="text-muted">(Free)</span>'}
                            </label>
                        </div>
                        <div class="form-check">
                            <input type="radio" 
                                   class="form-check-input item-boolean-input" 
                                   id="field_${item.id}_no" 
                                   name="item_field_${item.id}" 
                                   value="no"
                                   data-item-id="${item.id}"
                                   data-price-type="${noConfig.price_type}"
                                   data-price-value="${noConfig.price_value}">
                            <label class="form-check-label" for="field_${item.id}_no">
                                No ${noConfig.price_type === 'paid' ? '<span class="text-success">($' + noConfig.price_value + ')</span>' : '<span class="text-muted">(Free)</span>'}
                            </label>
                        </div>
                    </div>
                `;
            }
            
            // For select field type with option pricing
            if (item.field_type === 'select' && item.option_pricing && item.field_options) {
                let options = '<option value="">Choose...</option>';
                item.field_options.forEach(option => {
                    const optionKey = option.toLowerCase();
                    const optionConfig = item.option_pricing[optionKey] || { price_type: 'free', price_value: 0 };
                    const priceText = optionConfig.price_type === 'paid' 
                        ? ` - $${optionConfig.price_value}` 
                        : ' - Free';
                    
                    options += `<option value="${option}" 
                                        data-price-type="${optionConfig.price_type}" 
                                        data-price-value="${optionConfig.price_value}">${option}${priceText}</option>`;
                });
                
                return `
                    <div class="form-group">
                        <label for="field_${item.id}">Select an option:</label>
                        <select class="form-select item-select-input" 
                                id="field_${item.id}" 
                                name="item_field_${item.id}"
                                data-item-id="${item.id}">
                            ${options}
                        </select>
                    </div>
                `;
            }
            
            // Legacy/fallback rendering for items without option pricing
            switch(item.field_type) {
                case 'text':
                    return `
                        <div class="form-group">
                            <label for="field_${item.id}">Value:</label>
                            <input type="text" 
                                   class="form-control" 
                                   id="field_${item.id}" 
                                   name="item_field_${item.id}" 
                                   placeholder="Enter text">
                        </div>
                    `;
                case 'textarea':
                    return `
                        <div class="form-group">
                            <label for="field_${item.id}">Value:</label>
                            <textarea class="form-control" 
                                      id="field_${item.id}" 
                                      name="item_field_${item.id}" 
                                      rows="3" 
                                      placeholder="Enter details"></textarea>
                        </div>
                    `;
                case 'number':
                    return `
                        <div class="form-group">
                            <label for="field_${item.id}">Quantity: <span class="text-muted small">(Max: ${item.max_quantity})</span></label>
                            <input type="number" 
                                   class="form-control item-number-input" 
                                   id="field_${item.id}" 
                                   name="item_field_${item.id}"
                                   data-item-id="${item.id}" 
                                   placeholder="Enter quantity"
                                   min="1"
                                   max="${item.max_quantity}"
                                   value="1">
                        </div>
                    `;
                case 'boolean':
                    return `
                        <div class="form-group">
                            <label>Select an option:</label>
                            <div class="form-check">
                                <input type="radio" 
                                       class="form-check-input" 
                                       id="field_${item.id}_yes" 
                                       name="item_field_${item.id}" 
                                       value="yes">
                                <label class="form-check-label" for="field_${item.id}_yes">Yes</label>
                            </div>
                            <div class="form-check">
                                <input type="radio" 
                                       class="form-check-input" 
                                       id="field_${item.id}_no" 
                                       name="item_field_${item.id}" 
                                       value="no">
                                <label class="form-check-label" for="field_${item.id}_no">No</label>
                            </div>
                        </div>
                    `;
                case 'select':
                    let options = '<option value="">Choose...</option>';
                    if (item.field_options && Array.isArray(item.field_options)) {
                        item.field_options.forEach(option => {
                            options += `<option value="${option}">${option}</option>`;
                        });
                    }
                    return `
                        <div class="form-group">
                            <label for="field_${item.id}">Select an option:</label>
                            <select class="form-select" 
                                    id="field_${item.id}" 
                                    name="item_field_${item.id}">
                                ${options}
                            </select>
                        </div>
                    `;
                default:
                    return `
                        <div class="form-group">
                            <label for="field_${item.id}">Value:</label>
                            <input type="text" 
                                   class="form-control" 
                                   id="field_${item.id}" 
                                   name="item_field_${item.id}" 
                                   placeholder="Enter value">
                        </div>
                    `;
            }
        }
        
        // Add event listeners to checkboxes
        document.querySelectorAll('.service-item-checkbox-input').forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const itemId = this.value;
                const item = serviceItems.find(i => i.id === itemId);
                const fieldContainer = document.getElementById(`field_container_${itemId}`);
                const isRequired = this.dataset.required === 'true';
                
                // Prevent unchecking required items
                if (isRequired && !this.checked) {
                    this.checked = true;
                    return;
                }
                
                if (this.checked) {
                    const itemData = serviceItems.find(i => i.id === itemId);
                    
                    // Initialize with default price (will be updated by field selection)
                    let initialPrice = 0;
                    if (item.field_type === 'number' && item.price_type === 'paid') {
                        initialPrice = parseFloat(item.price_value);
                    }
                    
                    selectedItems[itemId] = {
                        name: itemData ? itemData.name : 'Unknown Item',
                        price: initialPrice,
                        quantity: 1,
                        duration: itemData ? parseInt(itemData.duration_minutes || 0) : 0,
                        inputValue: null,  // Will store user input value
                        fieldType: item.field_type,
                        optionPricing: item.option_pricing
                    };
                    
                    // Show field container
                    if (fieldContainer) {
                        fieldContainer.classList.remove('d-none');
                    }
                    
                    // Show quantity control if max_quantity > 1
                    if (item && item.max_quantity > 1) {
                        const quantityControl = this.closest('.card-body').querySelector('.quantity-control');
                        if (quantityControl) {
                            quantityControl.classList.remove('d-none');
                        }
                    }
                } else {
                    delete selectedItems[itemId];
                    
                    // Hide field container
                    if (fieldContainer) {
                        fieldContainer.classList.add('d-none');
                    }
                    
                    // Hide quantity control
                    const quantityControl = this.closest('.card-body').querySelector('.quantity-control');
                    if (quantityControl) {
                        quantityControl.classList.add('d-none');
                    }
                }
                
                updateTotalPrice();
            });
        });
        
        // Add event listeners to quantity controls
        document.querySelectorAll('.decrease-qty').forEach(btn => {
            btn.addEventListener('click', function() {
                const itemId = this.dataset.itemId;
                const input = document.getElementById(`quantity_${itemId}`);
                const currentValue = parseInt(input.value);
                if (currentValue > 1) {
                    input.value = currentValue - 1;
                    if (selectedItems[itemId]) {
                        selectedItems[itemId].quantity = currentValue - 1;
                        updateTotalPrice();
                    }
                }
            });
        });
        
        document.querySelectorAll('.increase-qty').forEach(btn => {
            btn.addEventListener('click', function() {
                const itemId = this.dataset.itemId;
                const input = document.getElementById(`quantity_${itemId}`);
                const currentValue = parseInt(input.value);
                const maxValue = parseInt(input.max);
                if (currentValue < maxValue) {
                    input.value = currentValue + 1;
                    if (selectedItems[itemId]) {
                        selectedItems[itemId].quantity = currentValue + 1;
                        updateTotalPrice();
                    }
                }
            });
        });
        
        document.querySelectorAll('.item-quantity').forEach(input => {
            input.addEventListener('change', function() {
                const itemId = this.id.replace('quantity_', '');
                const value = parseInt(this.value);
                if (selectedItems[itemId]) {
                    selectedItems[itemId].quantity = value;
                    updateTotalPrice();
                }
            });
        });
        
        // Add event listeners to number inputs (for quantity-based pricing)
        document.querySelectorAll('.item-number-input').forEach(input => {
            input.addEventListener('input', function() {
                // Remove validation error when user starts typing
                this.classList.remove('is-invalid');
                
                const itemId = this.dataset.itemId;
                const item = serviceItems.find(i => i.id === itemId);
                const quantity = parseInt(this.value) || 0;
                
                if (selectedItems[itemId] && item) {
                    // Enforce max_quantity
                    if (quantity > item.max_quantity) {
                        this.value = item.max_quantity;
                        selectedItems[itemId].quantity = item.max_quantity;
                    } else {
                        selectedItems[itemId].quantity = quantity;
                    }
                    selectedItems[itemId].inputValue = selectedItems[itemId].quantity;
                    
                    // Calculate price: base price * quantity
                    selectedItems[itemId].price = parseFloat(item.price_value) * selectedItems[itemId].quantity;
                    
                    updateTotalPrice();
                }
            });
        });
        
        // Add event listeners to boolean inputs (Yes/No with option pricing)
        document.querySelectorAll('.item-boolean-input').forEach(input => {
            input.addEventListener('change', function() {
                // Remove validation error when user selects an option
                const formGroup = this.closest('.form-group');
                if (formGroup) {
                    formGroup.classList.remove('is-invalid');
                }
                
                if (this.checked) {
                    const itemId = this.dataset.itemId;
                    const priceType = this.dataset.priceType;
                    const priceValue = parseFloat(this.dataset.priceValue) || 0;
                    
                    console.log('Boolean input changed:', {
                        itemId,
                        value: this.value,
                        priceType,
                        priceValue,
                        selectedItems: selectedItems[itemId]
                    });
                    
                    if (selectedItems[itemId]) {
                        selectedItems[itemId].inputValue = this.value;
                        
                        // Update price based on selected option
                        if (priceType === 'paid') {
                            selectedItems[itemId].price = priceValue;
                        } else {
                            selectedItems[itemId].price = 0;
                        }
                        
                        console.log('Updated item price:', selectedItems[itemId].price);
                        updateTotalPrice();
                    } else {
                        console.warn('Item not in selectedItems:', itemId);
                    }
                }
            });
        });
        
        // Add event listeners to select inputs (dropdown with option pricing)
        document.querySelectorAll('.item-select-input').forEach(input => {
            input.addEventListener('change', function() {
                // Remove validation error when user selects an option
                this.classList.remove('is-invalid');
                
                const itemId = this.dataset.itemId;
                const selectedOption = this.options[this.selectedIndex];
                
                console.log('Select input changed:', {
                    itemId,
                    value: this.value,
                    selectedOption,
                    selectedItems: selectedItems[itemId]
                });
                
                if (selectedItems[itemId] && selectedOption && this.value) {
                    selectedItems[itemId].inputValue = this.value;
                    
                    // Get pricing from selected option
                    const priceType = selectedOption.dataset.priceType;
                    const priceValue = parseFloat(selectedOption.dataset.priceValue) || 0;
                    
                    console.log('Option pricing:', { priceType, priceValue });
                    
                    if (priceType === 'paid') {
                        selectedItems[itemId].price = priceValue;
                    } else {
                        selectedItems[itemId].price = 0;
                    }
                    
                    console.log('Updated item price:', selectedItems[itemId].price);
                    updateTotalPrice();
                } else {
                    console.warn('Item not in selectedItems or no option selected:', itemId);
                }
            });
        });
        
        // Add event listeners to other field inputs (text, textarea)
        document.querySelectorAll('input[id^="field_"]:not(.item-number-input):not(.item-boolean-input), textarea[id^="field_"], select[id^="field_"]:not(.item-select-input)').forEach(input => {
            input.addEventListener('input', function() {
                const itemId = this.id.replace('field_', '');
                if (selectedItems[itemId]) {
                    selectedItems[itemId].inputValue = this.value;
                }
            });
        });
        
        // Initialize selected items from required items
        console.log('=== INITIALIZING REQUIRED ITEMS ===');
        items.forEach(item => {
            if (!item.is_optional) {  // Required items (is_optional = false)
                console.log('Adding required item:', item.id, item.name);
                
                // Initialize with default price (0 for items that need user selection)
                let initialPrice = 0;
                if (item.field_type === 'number' && item.price_type === 'paid') {
                    initialPrice = parseFloat(item.price_value);
                }
                
                selectedItems[item.id] = {
                    name: item.name,
                    price: initialPrice,
                    quantity: 1,
                    duration: parseInt(item.duration_minutes || 0),
                    inputValue: null,  // Will store user input value
                    fieldType: item.field_type,
                    optionPricing: item.option_pricing
                };
            }
        });
        console.log('Total selected items after initialization:', Object.keys(selectedItems).length);
        
        updateTotalPrice();
    }

    // Industry-specific fields functionality has been removed as requested

    // Calculate and update total price and duration
    function updateTotalPrice() {
        totalPrice = basePrice;
        totalDuration = baseDuration;
        
        console.log('=== UPDATE TOTAL PRICE ===');
        console.log('Base price:', basePrice);
        console.log('Selected items:', selectedItems);
        
        // Add prices and durations of selected items
        Object.entries(selectedItems).forEach(([itemId, item]) => {
            const itemPrice = item.price * item.quantity;
            console.log(`Item ${itemId} (${item.name}):`, {
                price: item.price,
                quantity: item.quantity,
                total: itemPrice
            });
            totalPrice += itemPrice;
            totalDuration += item.duration * item.quantity;
        });
        
        console.log('Total price:', totalPrice);
        
        if (totalPriceSpan) totalPriceSpan.textContent = totalPrice.toFixed(2);
        
        // Dispatch event for multi-step form to update summary
        if (isMultiStepForm) {
            console.log('=== DISPATCHING SERVICE ITEMS UPDATED EVENT ===');
            console.log('Selected items to dispatch:', selectedItems);
            console.log('Selected items count:', Object.keys(selectedItems).length);
            
            const event = new CustomEvent('serviceItemsUpdated', {
                detail: { items: selectedItems }
            });
            document.dispatchEvent(event);
        }
        
        // Update service duration display
        if (serviceDurationSpan) {
            serviceDurationSpan.textContent = totalDuration;
        }
        
        // Update summary duration display
        if (summaryDuration) {
            const hours = Math.floor(totalDuration / 60);
            const minutes = totalDuration % 60;
            let durationText = '';
            
            if (hours > 0) {
                durationText += `${hours} hour${hours > 1 ? 's' : ''}`;
                if (minutes > 0) durationText += ' ';
            }
            
            if (minutes > 0 || hours === 0) {
                durationText += `${minutes} minute${minutes !== 1 ? 's' : ''}`;
            }
            
            summaryDuration.textContent = durationText;
        }
        
        // Recalculate end time if start time is set
        if (startTimeInput && startTimeInput.value) {
            calculateEndTime(startTimeInput.value, totalDuration);
        }
        
        // Update booking summary
        updateBookingSummary();
    }
    
    // Update booking summary
    function updateBookingSummary() {
        // Check for selected service from either select or radio buttons
        let serviceName = '';
        let hasService = false;
        
        if (serviceTypeSelect && serviceTypeSelect.tagName === 'SELECT' && serviceTypeSelect.value) {
            serviceName = serviceTypeSelect.options[serviceTypeSelect.selectedIndex].text;
            hasService = true;
        } else {
            // Check radio buttons
            const selectedRadio = document.querySelector('input[name="service_type"]:checked');
            if (selectedRadio) {
                serviceName = selectedRadio.dataset.name || selectedRadio.value;
                hasService = true;
            }
        }
        
        if (!hasService) return;
        
        if (summaryService) summaryService.textContent = serviceName;
        
        // Format date and time
        if (summaryDateTime) {
            if (bookingDateInput && bookingDateInput.value && startTimeInput && startTimeInput.value && endTimeInput && endTimeInput.value) {
                const formattedDate = new Date(bookingDateInput.value).toLocaleDateString();
                summaryDateTime.textContent = `${formattedDate}, ${formatTime(startTimeInput.value)} - ${formatTime(endTimeInput.value)}`;
            } else {
                summaryDateTime.textContent = '-';
            }
        }
        
        // Format duration in summary
        if (summaryDuration) {
            if (totalDuration > 0) {
                const hours = Math.floor(totalDuration / 60);
                const minutes = totalDuration % 60;
                let durationText = '';
                
                if (hours > 0) {
                    durationText += `${hours} hour${hours > 1 ? 's' : ''}`;
                    if (minutes > 0) durationText += ' ';
                }
                
                if (minutes > 0 || hours === 0) {
                    durationText += `${minutes} minute${minutes !== 1 ? 's' : ''}`;
                }
                
                summaryDuration.textContent = durationText;
            } else {
                summaryDuration.textContent = '-';
            }
        }
        
        // Format location
        if (summaryLocation && locationTypeSelect) {
            const locationType = locationTypeSelect.value;
            let locationText = '';
            
            switch (locationType) {
                case 'business':
                    locationText = 'At Business Location';
                    break;
                case 'onsite':
                    locationText = 'On-site (Client Location)';
                    if (locationDetailsInput && locationDetailsInput.value) {
                        locationText += `: ${locationDetailsInput.value}`;
                    }
                    break;
                case 'virtual':
                    locationText = 'Virtual Meeting';
                    if (locationDetailsInput && locationDetailsInput.value) {
                        locationText += `: ${locationDetailsInput.value}`;
                    }
                    break;
                default:
                    locationText = '-';
            }
            
            summaryLocation.textContent = locationText;
        }
        
        if (bookingSummary) bookingSummary.classList.remove('d-none');
    }

    // Format time from 24h to 12h format
    function formatTime(time24) {
        const [hours, minutes] = time24.split(':');
        const hour = parseInt(hours, 10);
        const period = hour >= 12 ? 'PM' : 'AM';
        const hour12 = hour % 12 || 12;
        return `${hour12}:${minutes} ${period}`;
    }

    // Form validation and submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        let valid = true;
        form.querySelectorAll('[required]').forEach(function(input) {
            // Handle radio buttons differently
            if (input.type === 'radio') {
                const radioGroup = form.querySelectorAll(`input[name="${input.name}"]`);
                const isAnyChecked = Array.from(radioGroup).some(radio => radio.checked);
                if (!isAnyChecked) {
                    valid = false;
                    radioGroup.forEach(radio => radio.classList.add('is-invalid'));
                } else {
                    radioGroup.forEach(radio => radio.classList.remove('is-invalid'));
                }
            } 
            // Handle checkboxes
            else if (input.type === 'checkbox') {
                if (!input.checked) {
                    valid = false;
                    input.classList.add('is-invalid');
                } else {
                    input.classList.remove('is-invalid');
                }
            }
            // Handle all other input types (text, email, tel, date, time, select, etc.)
            else {
                if (!input.value || !input.value.trim()) {
                    valid = false;
                    input.classList.add('is-invalid');
                } else {
                    input.classList.remove('is-invalid');
                }
            }
        });
        
        // First, check all service items with values and ensure their checkboxes are checked
        // This ensures that items with values are included in the form submission
        document.querySelectorAll('.service-item-checkbox-input').forEach(function(checkbox) {
            const itemId = checkbox.value;
            const fieldType = checkbox.dataset.fieldType;
            const priceType = checkbox.dataset.priceType;
            let hasValue = false;
            
            // Check if this item has a value
            if (fieldType === 'boolean') {
                // For ALL boolean fields (free or with option pricing)
                const yesRadio = document.getElementById(`field_${itemId}_yes`);
                const noRadio = document.getElementById(`field_${itemId}_no`);
                if ((yesRadio && yesRadio.checked) || (noRadio && noRadio.checked)) {
                    hasValue = true;
                }
            } else {
                const fieldInput = document.getElementById(`field_${itemId}`);
                if (fieldInput && fieldInput.value && fieldInput.value.trim()) {
                    hasValue = true;
                }
            }
            
            // If the item has a value, check it
            if (hasValue) {
                checkbox.checked = true;
            }
        });
        
        // Now validate all checked items
        document.querySelectorAll('.service-item-checkbox-input:checked').forEach(function(checkbox) {
            const itemId = checkbox.value;
            const fieldType = checkbox.dataset.fieldType;
            const priceType = checkbox.dataset.priceType;
            
            // Handle different field types - prioritize field type over price type
            if (fieldType === 'select') {
                // For ALL select fields (free or with option pricing), ensure an option is selected
                const fieldInput = document.getElementById(`field_${itemId}`);
                if (fieldInput && !fieldInput.value) {
                    valid = false;
                    fieldInput.classList.add('is-invalid');
                }
            } else if (fieldType === 'boolean') {
                // For ALL boolean fields (free or with option pricing), check if either Yes or No is selected
                const yesRadio = document.getElementById(`field_${itemId}_yes`);
                const noRadio = document.getElementById(`field_${itemId}_no`);
                if (!yesRadio || !noRadio || (!yesRadio.checked && !noRadio.checked)) {
                    valid = false;
                    if (yesRadio && yesRadio.closest('.form-group')) {
                        yesRadio.closest('.form-group').classList.add('is-invalid');
                    }
                }
            } else if (fieldType === 'number') {
                // For number fields, ensure a valid number is entered
                const fieldInput = document.getElementById(`field_${itemId}`);
                if (fieldInput && (!fieldInput.value || isNaN(parseFloat(fieldInput.value)) || parseFloat(fieldInput.value) <= 0)) {
                    valid = false;
                    fieldInput.classList.add('is-invalid');
                }
            } else if (fieldType === 'text' || fieldType === 'textarea') {
                // For text/textarea fields, just check if they're not empty
                const fieldInput = document.getElementById(`field_${itemId}`);
                if (fieldInput && !fieldInput.value.trim()) {
                    valid = false;
                    fieldInput.classList.add('is-invalid');
                }
            }
        });
        
        // Prepare selected items data
        const selectedItemsData = {};
        
        // Create a hidden input for each selected service item's field value
        if (valid) {
            console.log('Checked checkboxes count:', document.querySelectorAll('.service-item-checkbox-input:checked').length);
            
            document.querySelectorAll('.service-item-checkbox-input:checked').forEach(function(checkbox) {
                const itemId = checkbox.value;
                const fieldType = checkbox.dataset.fieldType;
                const priceType = checkbox.dataset.priceType;
                const quantityInput = document.getElementById(`quantity_${itemId}`);
                let fieldValue = '';
                
                // Handle different field types
                if (fieldType === 'boolean') {
                    // For ALL boolean fields (free or with option pricing)
                    const yesRadio = document.getElementById(`field_${itemId}_yes`);
                    const noRadio = document.getElementById(`field_${itemId}_no`);
                    if (yesRadio && yesRadio.checked) {
                        fieldValue = yesRadio.value; // 'yes' or 'true'
                    } else if (noRadio && noRadio.checked) {
                        fieldValue = noRadio.value; // 'no' or 'false'
                    }
                } else {
                    // For other field types (text, textarea, number, select)
                    const fieldInput = document.getElementById(`field_${itemId}`);
                    if (fieldInput) {
                        fieldValue = fieldInput.value;
                    }
                }
                
                selectedItemsData[itemId] = {
                    value: fieldValue,
                    quantity: quantityInput ? parseInt(quantityInput.value) : 1
                };
                
                console.log(`Item ${itemId} (${fieldType}):`, {
                    value: fieldValue,
                    quantity: quantityInput ? parseInt(quantityInput.value) : 1
                });
            });
            
            console.log('=== FINAL SELECTED ITEMS DATA ===');
            console.log('Selected items data:', selectedItemsData);
            console.log('Selected items data JSON:', JSON.stringify(selectedItemsData));
            
            // Add the selected items data as a hidden input
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'selected_items_data';
            hiddenInput.value = JSON.stringify(selectedItemsData);
            form.appendChild(hiddenInput);
        }
        
        if (!valid) {
            // Find which field is missing
            const firstInvalid = form.querySelector('.is-invalid');
            let fieldName = 'Unknown field';
            
            if (firstInvalid) {
                // Check if it's a service item field
                if (firstInvalid.id && firstInvalid.id.startsWith('field_')) {
                    // Extract item ID from field_XXX
                    const itemId = firstInvalid.id.replace('field_', '').split('_')[0];
                    const itemCheckbox = document.querySelector(`.service-item-checkbox-input[value="${itemId}"]`);
                    if (itemCheckbox) {
                        const itemCard = itemCheckbox.nextElementSibling;
                        const itemTitle = itemCard ? itemCard.querySelector('.service-item-title') : null;
                        if (itemTitle) {
                            fieldName = itemTitle.textContent.trim();
                        } else {
                            fieldName = 'Service Item';
                        }
                    }
                } else {
                    // Try to get the field label for regular form fields
                    const label = form.querySelector(`label[for="${firstInvalid.id}"]`);
                    if (label) {
                        fieldName = label.textContent.replace('*', '').trim();
                    } else if (firstInvalid.name === 'service_type') {
                        fieldName = 'Service Type';
                    } else if (firstInvalid.name) {
                        fieldName = firstInvalid.name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    }
                }
                
                alert(`Please fill in all required fields. Missing: ${fieldName}`);
                firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else {
                alert('Please fill in all required fields.');
            }
            return;
        }
        
        // If valid, submit the booking via API
        try {
            // Get widget state from global
            const widgetState = window.BookingWidget;
            
            const submitBtn = document.getElementById('submit-booking-btn');
            const successMessage = document.getElementById('booking-success-message');
            const errorMessage = document.getElementById('booking-error-message');
            
            // Disable submit button
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Creating Booking...';
            }
            
            // Hide previous messages
            if (successMessage) successMessage.classList.add('d-none');
            if (errorMessage) errorMessage.classList.add('d-none');
            
            // Collect custom fields data
            const customFieldsData = {};
            widgetState.customFields.forEach(field => {
                const fieldKey = `custom_${field.slug}`;
                const fieldElement = document.getElementById(fieldKey);
                if (fieldElement) {
                    if (field.field_type === 'boolean') {
                        customFieldsData[fieldKey] = fieldElement.checked;
                    } else {
                        customFieldsData[fieldKey] = fieldElement.value;
                    }
                }
            });
            
            // Get selected service
            const selectedServiceRadio = document.querySelector('input[name="service_type"]:checked');
            
            // Prepare booking data
            const bookingData = {
                service_type: selectedServiceRadio ? selectedServiceRadio.value : '',
                booking_date: document.getElementById('booking_date').value,
                start_time: document.getElementById('start_time').value,
                end_time: document.getElementById('end_time').value,
                location_type: document.getElementById('location_type').value,
                location_details: document.getElementById('location_details').value,
                notes: document.getElementById('notes').value,
                staff_member_id: document.getElementById('staff_member_id').value,
                client_name: document.getElementById('client_name').value,
                client_email: document.getElementById('client_email').value,
                client_phone: document.getElementById('client_phone').value,
                custom_fields: customFieldsData,
                service_items: selectedItemsData
            };
            
            console.log('Submitting booking data:', bookingData);
            
            // Submit to widget API
            const response = await fetch(`${widgetState.apiBaseUrl}/bookings/widget/${widgetState.businessId}/create/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(bookingData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Show success message
                if (successMessage) {
                    successMessage.classList.remove('d-none');
                    successMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                
                // Reset form after 3 seconds
                setTimeout(() => {
                    form.reset();
                    selectedItems = {};
                    updateTotalPrice();
                    // Go back to step 1
                    if (typeof showStep === 'function') {
                        showStep(1);
                    }
                }, 3000);
            } else {
                // Show error message
                if (errorMessage) {
                    errorMessage.textContent = result.error || 'An error occurred while creating the booking.';
                    errorMessage.classList.remove('d-none');
                    errorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
            
        } catch (error) {
            console.error('Booking submission error:', error);
            const errorMessage = document.getElementById('booking-error-message');
            if (errorMessage) {
                errorMessage.textContent = 'An error occurred while creating the booking. Please try again.';
                errorMessage.classList.remove('d-none');
                errorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        } finally {
            // Re-enable submit button
            const submitBtn = document.getElementById('submit-booking-btn');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-check me-2"></i>Confirm Booking';
            }
        }
    });

    // Remove highlight on input
    form.querySelectorAll('[required]').forEach(function(input) {
        if (input.type === 'radio') {
            input.addEventListener('change', function() {
                const radioGroup = form.querySelectorAll(`input[name="${input.name}"]`);
                radioGroup.forEach(radio => radio.classList.remove('is-invalid'));
            });
        } else if (input.type === 'checkbox') {
            input.addEventListener('change', function() {
                if (input.checked) {
                    input.classList.remove('is-invalid');
                }
            });
        } else {
            input.addEventListener('input', function() {
                if (input.value) {
                    input.classList.remove('is-invalid');
                }
            });
        }
    });
    }
})();
