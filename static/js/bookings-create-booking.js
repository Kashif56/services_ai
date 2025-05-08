// bookings-create-booking.js - Enhance Create Booking page with dynamic fields and pricing

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('create-booking-form');
    if (!form) return;

    // Cache DOM elements
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

    // State variables
    let selectedServiceId = null;
    let basePrice = 0;
    let serviceItems = [];
    let selectedItems = {};
    let totalPrice = 0;
    let availabilityCheckTimeout = null;

    // Service selection change handler
    if (serviceTypeSelect) {
        serviceTypeSelect.addEventListener('change', function() {
            const serviceId = this.value;
            selectedServiceId = serviceId;
            
            if (serviceId) {
                const selectedOption = this.options[this.selectedIndex];
                const duration = selectedOption.dataset.duration;
                const price = selectedOption.dataset.price;
                basePrice = parseFloat(price);
                
                // Update service details
                serviceDurationSpan.textContent = duration;
                servicePriceSpan.textContent = price;
                serviceDetailsDiv.classList.remove('d-none');
                
                // Calculate end time based on start time and duration
                if (startTimeInput.value) {
                    calculateEndTime(startTimeInput.value, parseInt(duration));
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
                serviceDetailsDiv.classList.add('d-none');
                // Service items section remains visible, just update content
                serviceItemsContainer.innerHTML = '<div class="alert alert-info">Please select a service to view available items</div>';
                bookingSummary.classList.add('d-none');
                basePrice = 0;
                totalPrice = 0;
                updateTotalPrice();
                
                // Reset staff selection
                resetStaffSelection();
            }
        });
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
            if (selectedServiceId) {
                const selectedOption = serviceTypeSelect.options[serviceTypeSelect.selectedIndex];
                const duration = parseInt(selectedOption.dataset.duration);
                calculateEndTime(this.value, duration);
            }
            updateBookingSummary();
            
            // Check staff availability when time changes
            if (selectedServiceId && bookingDateInput.value && endTimeInput.value) {
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
        if (!startTime) return;
        
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
        
        // Make the actual API call to the correct endpoint
        fetch(`/bookings/api/service-items/${serviceId}/`)
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
            
            // Get the duration from the selected service
            let duration = 60; // Default duration
            if (selectedServiceId) {
                const selectedOption = serviceTypeSelect.options[serviceTypeSelect.selectedIndex];
                if (selectedOption && selectedOption.dataset.duration) {
                    duration = parseInt(selectedOption.dataset.duration);
                }
            }
            
            // Make API call to check availability
            const url = `/bookings/api/check-availability/?date=${date}&time=${startTime}&duration_minutes=${duration}`;
            
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
            html += `
                <div class="col-md-6 mb-3">
                    <div class="card h-100 bg-dark">
                        <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <h5 class="card-title">${item.name}</h5>
                            <span class="text-primary ${item.is_optional ? 'text-success' : 'text-danger'}">${item.is_optional ? 'Optional' : 'Required'}</span>
                        </div>
                            
                            
                            <p class="card-text">${item.description || ''}</p>
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="text-primary fw-bold">$${item.price_value}</span>
                                <div class="form-check form-switch">
                                    <input class="form-check-input service-item-checkbox" 
                                           type="checkbox" 
                                           id="item_${item.id}" 
                                           name="service_items[]" 
                                           value="${item.id}"
                                           data-price="${item.price_value}"
                                           ${item.is_optional ? '' : 'checked disabled'}>
                                    <label class="form-check-label" for="item_${item.id}">
                                        ${item.is_optional ? 'Add' : 'Required'}
                                    </label>
                                </div>
                            </div>
                            ${item.max_quantity > 1 ? `
                            <div class="mt-2 quantity-control ${item.is_optional && !selectedItems[item.id] ? 'd-none' : ''}">
                                <label for="quantity_${item.id}">Quantity:</label>
                                <div class="input-group input-group-sm">
                                    <button type="button" class="btn btn-outline-secondary decrease-qty" data-item-id="${item.id}">-</button>
                                    <input type="number" class="form-control text-center item-quantity" 
                                           id="quantity_${item.id}" 
                                           name="item_quantity_${item.id}" 
                                           min="1" 
                                           max="${item.max_quantity}" 
                                           value="${selectedItems[item.id]?.quantity || 1}">
                                    <button type="button" class="btn btn-outline-secondary increase-qty" data-item-id="${item.id}">+</button>
                                </div>
                            </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        serviceItemsContainer.innerHTML = html;
        
        // Add event listeners to checkboxes
        document.querySelectorAll('.service-item-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const itemId = this.value;
                const price = parseFloat(this.dataset.price);
                const item = serviceItems.find(i => i.id === itemId);
                
                if (this.checked) {
                    selectedItems[itemId] = {
                        price: price,
                        quantity: 1
                    };
                    
                    // Show quantity control if max_quantity > 1
                    if (item && item.max_quantity > 1) {
                        const quantityControl = this.closest('.card-body').querySelector('.quantity-control');
                        if (quantityControl) {
                            quantityControl.classList.remove('d-none');
                        }
                    }
                } else {
                    delete selectedItems[itemId];
                    
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
        
        // Initialize selected items from required items
        items.forEach(item => {
            if (item.is_required) {
                selectedItems[item.id] = {
                    price: parseFloat(item.price_value),
                    quantity: 1
                };
            }
        });
        
        updateTotalPrice();
    }

    // Industry-specific fields functionality has been removed as requested

    // Calculate and update total price
    function updateTotalPrice() {
        totalPrice = basePrice;
        
        // Add prices of selected items
        Object.values(selectedItems).forEach(item => {
            totalPrice += item.price * item.quantity;
        });
        
        totalPriceSpan.textContent = totalPrice.toFixed(2);
    }

    // Update booking summary
    function updateBookingSummary() {
        if (!selectedServiceId) {
            bookingSummary.classList.add('d-none');
            return;
        }
        
        const serviceName = serviceTypeSelect.options[serviceTypeSelect.selectedIndex].text;
        summaryService.textContent = serviceName;
        
        // Format date and time
        if (bookingDateInput.value && startTimeInput.value && endTimeInput.value) {
            const formattedDate = new Date(bookingDateInput.value).toLocaleDateString();
            summaryDateTime.textContent = `${formattedDate}, ${formatTime(startTimeInput.value)} - ${formatTime(endTimeInput.value)}`;
        } else {
            summaryDateTime.textContent = '-';
        }
        
        // Format location
        const locationType = locationTypeSelect.value;
        let locationText = '';
        
        switch (locationType) {
            case 'business':
                locationText = 'At Business Location';
                break;
            case 'onsite':
                locationText = 'On-site (Client Location)';
                if (locationDetailsInput.value) {
                    locationText += `: ${locationDetailsInput.value}`;
                }
                break;
            case 'virtual':
                locationText = 'Virtual Meeting';
                if (locationDetailsInput.value) {
                    locationText += `: ${locationDetailsInput.value}`;
                }
                break;
            default:
                locationText = '-';
        }
        
        summaryLocation.textContent = locationText;
        bookingSummary.classList.remove('d-none');
    }

    // Format time from 24h to 12h format
    function formatTime(time24) {
        const [hours, minutes] = time24.split(':');
        const hour = parseInt(hours, 10);
        const period = hour >= 12 ? 'PM' : 'AM';
        const hour12 = hour % 12 || 12;
        return `${hour12}:${minutes} ${period}`;
    }

    // Form validation
    form.addEventListener('submit', function(e) {
        let valid = true;
        form.querySelectorAll('[required]').forEach(function(input) {
            if (!input.value) {
                input.classList.add('is-invalid');
                valid = false;
            } else {
                input.classList.remove('is-invalid');
            }
        });
        
        if (!valid) {
            e.preventDefault();
            // Scroll to first invalid field
            const firstInvalid = form.querySelector('.is-invalid');
            if (firstInvalid) {
                firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    });

    // Remove highlight on input
    form.querySelectorAll('[required]').forEach(function(input) {
        input.addEventListener('input', function() {
            if (input.value) {
                input.classList.remove('is-invalid');
            }
        });
    });
});
