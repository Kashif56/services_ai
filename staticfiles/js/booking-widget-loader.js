/**
 * Booking Widget Loader
 * Embeddable booking form widget for third-party websites
 * 
 * Usage:
 * <div id="booking-widget" data-business-slug="your-business-slug"></div>
 * <script src="https://yourdomain.com/static/js/booking-widget-loader.js"></script>
 */

(function() {
    'use strict';
    
    // Get the widget container
    const widgetContainer = document.getElementById('booking-widget');
    if (!widgetContainer) {
        console.error('Booking Widget: Container element with id="booking-widget" not found');
        return;
    }
    
    // Get configuration from data attributes
    const businessId = widgetContainer.dataset.businessId;
    const apiBaseUrl = widgetContainer.dataset.apiUrl || window.location.origin;
    const primaryColor = widgetContainer.dataset.primaryColor || '#8b5cf6';
    const modalMode = widgetContainer.dataset.modalMode === 'true';
    
    if (!businessId) {
        console.error('Booking Widget: data-business-id attribute is required');
        widgetContainer.innerHTML = '<div style="padding: 20px; color: red;">Error: Business ID not provided</div>';
        return;
    }
    
    // Widget state
    const widgetState = {
        apiBaseUrl: apiBaseUrl,
        businessId: businessId,
        primaryColor: primaryColor,
        business: null,
        services: [],
        customFields: [],
        selectedService: null,
        serviceItems: [],
        selectedItems: {},
        currentStep: 1,
        totalSteps: 5,
        basePrice: 0,
        baseDuration: 0,
        totalPrice: 0,
        totalDuration: 0,
        formData: {
            client_name: '',
            client_email: '',
            client_phone: '',
            booking_date: '',
            start_time: '',
            end_time: '',
            location_type: 'business',
            location_details: '',
            notes: '',
            staff_member_id: '',
            custom_fields: {},
            service_items: {}
        }
    };
    
    // Load CSS
    function loadCSS() {
        // Add Font Awesome only
        const faLink = document.createElement('link');
        faLink.rel = 'stylesheet';
        faLink.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css';
        document.head.appendChild(faLink);
        
        // Add widget custom CSS (no Bootstrap needed)
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = `${apiBaseUrl}/static/css/booking-widget.css`;
        document.head.appendChild(link);
        
        // Add custom color styles and CSS isolation
        const style = document.createElement('style');
        style.textContent = `
            /* Widget color customization */
            #booking-widget {
                --primary: ${primaryColor};
                --primary-rgb: ${hexToRgb(primaryColor)};
            }
            
            /* Modal wrapper styling */
            .booking-widget-modal-wrapper {
                position: relative;
                max-width: 1200px;
                margin: 2rem auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-height: 90vh;
                overflow-y: auto;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                box-sizing: border-box;
            }
            
            .booking-widget-modal-wrapper * {
                box-sizing: border-box;
            }
            
            /* Ensure modal overlay is on top */
            #booking-widget-modal {
                z-index: 999999 !important;
            }
            
            /* Reset Tailwind interference for modal content */
            #booking-widget-modal-content * {
                font-family: inherit;
            }
        `;
        document.head.appendChild(style);
    }
    
    // Helper function to convert hex to RGB
    function hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? 
            `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` : 
            '139, 92, 246';
    }
    
    // Initialize widget
    async function initWidget() {
        try {
            // Show loading state
            widgetContainer.innerHTML = `
                <div style="padding: 40px; text-align: center;">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p style="margin-top: 10px;">Loading booking form...</p>
                </div>
            `;
            
            // Fetch widget configuration
            const response = await fetch(`${apiBaseUrl}/bookings/widget/${businessId}/config/`);
            if (!response.ok) {
                throw new Error('Failed to load widget configuration');
            }
            
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Failed to load widget');
            }
            
            widgetState.business = data.business;
            widgetState.services = data.services;
            widgetState.customFields = data.custom_fields;
            
            // Render the widget
            renderWidget();
            
            // Initialize event listeners
            initEventListeners();
            
        } catch (error) {
            console.error('Booking Widget Error:', error);
            widgetContainer.innerHTML = `
                <div style="padding: 20px; color: red; border: 1px solid red; border-radius: 5px;">
                    <strong>Error loading booking widget:</strong> ${error.message}
                </div>
            `;
        }
    }
    
    // Create modal container
    function createModal() {
        const modal = document.createElement('div');
        modal.id = 'booking-widget-modal';
        modal.style.cssText = `
            display: none;
            position: fixed;
            z-index: 999999;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0,0,0,0.7);
            backdrop-filter: blur(5px);
        `;
        
        modal.innerHTML = `
            <div class="booking-widget-modal-wrapper">
                <button id="close-booking-modal" style="position: absolute; top: 15px; right: 15px; z-index: 10; background: #ef4444; color: white; border: none; width: 40px; height: 40px; border-radius: 50%; cursor: pointer; font-size: 24px; line-height: 1; transition: all 0.3s ease; box-shadow: 0 2px 8px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center;">
                    &times;
                </button>
                <div id="booking-widget-modal-content"></div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close modal handlers
        const closeBtn = modal.querySelector('#close-booking-modal');
        closeBtn.addEventListener('click', closeModal);
        closeBtn.addEventListener('mouseenter', function() {
            this.style.background = '#dc2626';
            this.style.transform = 'scale(1.1)';
        });
        closeBtn.addEventListener('mouseleave', function() {
            this.style.background = '#ef4444';
            this.style.transform = 'scale(1)';
        });
        
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });
        
        return modal;
    }
    
    // Open modal
    function openModal() {
        const modal = document.getElementById('booking-widget-modal');
        if (modal) {
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden';
        }
    }
    
    // Close modal
    function closeModal() {
        const modal = document.getElementById('booking-widget-modal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }
    }
    
    // Render the widget HTML
    function renderWidget() {
        const targetContainer = modalMode ? document.getElementById('booking-widget-modal-content') : widgetContainer;
        
        if (!targetContainer) return;
        
        // Wrap content in #booking-widget for CSS scoping
        targetContainer.innerHTML = `
            <div id="booking-widget">
                <div class="booking-widget-container">
                <!-- Header -->
             
                
                <!-- Progress Steps -->
                <div class="card shadow-sm mb-4">
                    <div class="card-body p-3">
                        <div class="steps-progress">
                            <div class="step active" data-step="1">
                                <div class="step-number">1</div>
                                <div class="step-label">Client Info</div>
                            </div>
                            <div class="step-line"></div>
                            <div class="step" data-step="2">
                                <div class="step-number">2</div>
                                <div class="step-label">Service</div>
                            </div>
                            <div class="step-line"></div>
                            <div class="step" data-step="3">
                                <div class="step-number">3</div>
                                <div class="step-label">Items</div>
                            </div>
                            <div class="step-line"></div>
                            <div class="step" data-step="4">
                                <div class="step-number">4</div>
                                <div class="step-label">Date & Time</div>
                            </div>
                            <div class="step-line"></div>
                            <div class="step" data-step="5">
                                <div class="step-number">5</div>
                                <div class="step-label">Confirm</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Form Container -->
                <div class="row">
                    <div class="col-lg-8">
                        <div class="card shadow-sm">
                            <div class="card-body p-4">
                                <form id="widget-booking-form" novalidate>
                                    ${renderStep1()}
                                    ${renderStep2()}
                                    ${renderStep3()}
                                    ${renderStep4()}
                                    ${renderStep5()}
                                </form>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Summary Column -->
                    <div class="col-lg-4">
                        <div class="card shadow-sm sticky-summary">
                            <div class="card-header text-white">
                                <h5 class="mb-0"><i class="fas fa-receipt me-2"></i>Booking Summary</h5>
                            </div>
                            <div class="card-body">
                                <div class="summary-section mb-3 p-1">
                                    <h6 class="text-muted mb-2">Date & Time</h6>
                                    <div id="summary-datetime" class="summary-value">
                                        <i class="fas fa-calendar text-muted me-2"></i>Not selected yet
                                    </div>
                                </div>
                                
                                <div class="summary-section mb-3 p-1">
                                    <h6 class="text-muted mb-2">Duration</h6>
                                    <div id="summary-duration" class="summary-value">
                                        <i class="fas fa-clock text-muted me-2"></i>0 minutes
                                    </div>
                                </div>
                                
                                <div class="summary-section mb-3 p-1">
                                    <h6 class="text-muted mb-2">Service Type</h6>
                                    <div id="summary-service" class="summary-value">
                                        <i class="fas fa-briefcase text-muted me-2"></i>Not selected yet
                                    </div>
                                </div>
                                
                                <div class="summary-section mb-3 p-1">
                                    <h6 class="text-muted mb-2">Service Items</h6>
                                    <div id="summary-items" class="summary-value">
                                        <i class="fas fa-list text-muted me-2"></i>No items selected
                                    </div>
                                </div>
                                
                                <hr>
                                
                                <div class="price-breakdown">
                                    <div class="d-flex justify-content-between mb-2">
                                        <span>Service Base Price:</span>
                                        <span id="summary-base-price" class="fw-bold">$0.00</span>
                                    </div>
                                    <div class="d-flex justify-content-between mb-2">
                                        <span>Service Items Total:</span>
                                        <span id="summary-items-price" class="fw-bold">$0.00</span>
                                    </div>
                                    <div class="d-flex justify-content-between mb-2">
                                        <span>Tax:</span>
                                        <span id="summary-tax" class="fw-bold">$0.00</span>
                                    </div>
                                    <hr>
                                    <div class="d-flex justify-content-between">
                                        <h5 class="mb-0">Grand Total:</h5>
                                        <h5 class="mb-0 text-primary" id="summary-grand-total">$0.00</h5>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                </div>
            </div>
        `;
    }
    
    // Render Step 1: Client Information
    function renderStep1() {
        let customFieldsHTML = '';
        widgetState.customFields.forEach(field => {
            customFieldsHTML += renderCustomField(field);
        });
        
        return `
            <div class="form-step active" id="step-1">
                <h4 class="mb-4"><i class="fas fa-user me-2"></i>Client Information</h4>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="client_name" class="form-label">Full Name <span class="text-danger">*</span></label>
                        <input type="text" name="client_name" id="client_name" class="form-control" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="client_email" class="form-label">Email <span class="text-danger">*</span></label>
                        <input type="email" name="client_email" id="client_email" class="form-control" required>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="client_phone" class="form-label">Phone <span class="text-danger">*</span></label>
                        <input type="tel" name="client_phone" id="client_phone" class="form-control" required>
                    </div>
                </div>
                
                ${customFieldsHTML}
                
                <div class="d-flex justify-content-end mt-4">
                    <button type="button" class="btn btn-primary next-step" data-next="2">
                        Next: Service <i class="fas fa-arrow-right ms-2"></i>
                    </button>
                </div>
            </div>
        `;
    }
    
    // Render custom field
    function renderCustomField(field) {
        const requiredMark = field.required ? '<span class="text-danger">*</span>' : '';
        const requiredAttr = field.required ? 'required' : '';
        
        let fieldHTML = '';
        
        switch(field.field_type) {
            case 'text':
                fieldHTML = `<input type="text" name="custom_${field.slug}" id="custom_${field.slug}" class="form-control" ${requiredAttr} placeholder="${field.placeholder || ''}">`;
                break;
            case 'number':
                fieldHTML = `<input type="number" name="custom_${field.slug}" id="custom_${field.slug}" class="form-control" ${requiredAttr} placeholder="${field.placeholder || ''}">`;
                break;
            case 'textarea':
                fieldHTML = `<textarea name="custom_${field.slug}" id="custom_${field.slug}" class="form-control" rows="3" ${requiredAttr} placeholder="${field.placeholder || ''}"></textarea>`;
                break;
            case 'select':
                let options = '<option value="">Select an option</option>';
                field.options.forEach(opt => {
                    options += `<option value="${opt}">${opt}</option>`;
                });
                fieldHTML = `<select name="custom_${field.slug}" id="custom_${field.slug}" class="form-select" ${requiredAttr}>${options}</select>`;
                break;
            case 'boolean':
                fieldHTML = `
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" value="true" name="custom_${field.slug}" id="custom_${field.slug}">
                        <label class="form-check-label" for="custom_${field.slug}">Yes</label>
                    </div>
                `;
                break;
            default:
                fieldHTML = `<input type="text" name="custom_${field.slug}" id="custom_${field.slug}" class="form-control" ${requiredAttr} placeholder="${field.placeholder || ''}">`;
        }
        
        return `
            <div class="mb-3 custom-field">
                <label for="custom_${field.slug}" class="form-label">${field.name} ${requiredMark}</label>
                ${fieldHTML}
                ${field.help_text ? `<small class="form-text text-muted">${field.help_text}</small>` : ''}
            </div>
        `;
    }
    
    // Render Step 2: Service Selection
    function renderStep2() {
        let servicesHTML = '';
        widgetState.services.forEach(service => {
            servicesHTML += `
                <div class="service-tab-wrapper">
                    <input type="radio" 
                           name="service_type" 
                           id="service_${service.id}" 
                           value="${service.id}"
                           data-duration="${service.duration}" 
                           data-price="${service.price}"
                           data-name="${service.name}"
                           class="service-tab-input"
                           required>
                    <label for="service_${service.id}" class="service-tab-label">
                        <div class="service-tab-icon">
                            <i class="fas fa-briefcase"></i>
                        </div>
                        <div class="service-tab-content">
                            <div class="service-tab-name">${service.name}</div>
                            ${service.description ? `<div class="service-tab-desc">${service.description}</div>` : ''}
                            <div class="service-tab-details">
                                <span class="service-tab-price">$${service.price}</span>
                                <span class="service-tab-duration">${service.duration} min</span>
                            </div>
                        </div>
                    </label>
                </div>
            `;
        });
        
        return `
            <div class="form-step" id="step-2">
                <h4 class="mb-4"><i class="fas fa-briefcase me-2"></i>Select Service</h4>
                
                <div class="mb-4">
                    <label class="form-label d-block mb-3">Service Type <span class="text-danger">*</span></label>
                    <div class="service-tabs-container">
                        ${servicesHTML}
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="location_type" class="form-label">Location Type <span class="text-danger">*</span></label>
                        <select name="location_type" id="location_type" class="form-select" required>
                            <option value="business">Business Location</option>
                            <option value="onsite">On-site (Client Location)</option>
                            <option value="virtual">Virtual Meeting</option>
                        </select>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="location_details" class="form-label">Location Details</label>
                        <input type="text" name="location_details" id="location_details" class="form-control" placeholder="Enter address or meeting link">
                    </div>
                </div>
                
                <div class="d-flex justify-content-between mt-4">
                    <button type="button" class="btn btn-outline-secondary prev-step" data-prev="1">
                        <i class="fas fa-arrow-left me-2"></i>Previous
                    </button>
                    <button type="button" class="btn btn-primary next-step" data-next="3">
                        Next: Service Items <i class="fas fa-arrow-right ms-2"></i>
                    </button>
                </div>
            </div>
        `;
    }
    
    // Render Step 3: Service Items
    function renderStep3() {
        return `
            <div class="form-step" id="step-3">
                <h4 class="mb-4"><i class="fas fa-list me-2"></i>Service Items</h4>
                
                <div id="service-items-container">
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>Please select a service in the previous step to view available items
                    </div>
                </div>
                
                <div class="d-flex justify-content-between mt-4">
                    <button type="button" class="btn btn-outline-secondary prev-step" data-prev="2">
                        <i class="fas fa-arrow-left me-2"></i>Previous
                    </button>
                    <button type="button" class="btn btn-primary next-step" data-next="4">
                        Next: Date & Time <i class="fas fa-arrow-right ms-2"></i>
                    </button>
                </div>
            </div>
        `;
    }
    
    // Render Step 4: Date & Time
    function renderStep4() {
        return `
            <div class="form-step" id="step-4">
                <h4 class="mb-4"><i class="fas fa-calendar-alt me-2"></i>Date & Time Selection</h4>
                
                <div class="row">
                    <div class="col-md-6 mb-3" style="width: 50%;">
                        <label for="booking_date" class="form-label">Booking Date <span class="text-danger">*</span></label>
                        <input type="date" name="booking_date" id="booking_date" class="form-control" required>
                    </div>
                    <div class="col-md-6 mb-3" style="width: 50%;">
                        <label for="start_time" class="form-label">Start Time <span class="text-danger">*</span></label>
                        <input type="time" name="start_time" id="start_time" class="form-control" required>
                    </div>
                    <div class="col-md-6 mb-3" style="width: 50%;">
                        <label for="end_time" class="form-label">End Time <span class="text-danger">*</span></label>
                        <input type="time" name="end_time" id="end_time" class="form-control" required>
                    </div>
                </div>
                
                <div class="mb-3">
                    <label for="staff_member_id" class="form-label">Select Staff Member <span class="text-danger">*</span></label>
                    <select name="staff_member_id" id="staff_member_id" class="form-select" required>
                        <option value="">Select a staff member...</option>
                    </select>
                    <div id="staff-availability-message" class="form-text mt-2"></div>
                </div>
                
                <div id="alternate-timeslots-container" class="mt-3 d-none">
                    <div class="alert alert-warning">
                        <h6><i class="fas fa-exclamation-triangle me-2"></i>No staff available at selected time</h6>
                        <p class="mb-2">Consider these alternatives:</p>
                        <div id="alternate-timeslots"></div>
                    </div>
                </div>
                
                <div class="d-flex justify-content-between mt-4">
                    <button type="button" class="btn btn-outline-secondary prev-step" data-prev="3">
                        <i class="fas fa-arrow-left me-2"></i>Previous
                    </button>
                    <button type="button" class="btn btn-primary next-step" data-next="5">
                        Next: Confirm <i class="fas fa-arrow-right ms-2"></i>
                    </button>
                </div>
            </div>
        `;
    }
    
    // Render Step 5: Confirmation
    function renderStep5() {
        return `
            <div class="form-step" id="step-5">
                <h4 class="mb-4"><i class="fas fa-check-circle me-2"></i>Review & Confirm</h4>
                
                <div class="mb-3">
                    <label for="notes" class="form-label">Additional Notes</label>
                    <textarea name="notes" id="notes" class="form-control" rows="4" placeholder="Add any special instructions or notes for this booking..."></textarea>
                    <div class="form-text">Optional: Add any additional information or special requests</div>
                </div>
                
                <div id="booking-success-message" class="alert alert-success d-none">
                    <h5><i class="fas fa-check-circle me-2"></i>Booking Confirmed!</h5>
                    <p class="mb-0">Your booking has been successfully created. You will receive a confirmation email shortly.</p>
                </div>
                
                <div id="booking-error-message" class="alert alert-danger d-none"></div>
                
                <div class="d-flex justify-content-between mt-4">
                    <button type="button" class="btn btn-outline-secondary prev-step" data-prev="4">
                        <i class="fas fa-arrow-left me-2"></i>Previous
                    </button>
                    <button type="submit" class="btn btn-success btn-lg" id="submit-booking-btn">
                        <i class="fas fa-check me-2"></i>Confirm Booking
                    </button>
                </div>
            </div>
        `;
    }
    
    // Initialize event listeners
    function initEventListeners() {
        // Load the widget core and multistep scripts
        loadScript(`${apiBaseUrl}/static/js/booking-widget-core.js`, () => {
            loadScript(`${apiBaseUrl}/static/js/booking-widget-multistep.js`, () => {
                console.log('Booking widget initialized successfully');
            });
        });
    }
    
    // Load external script
    function loadScript(src, callback) {
        const script = document.createElement('script');
        script.src = src;
        script.onload = callback;
        script.onerror = () => {
            console.error(`Failed to load script: ${src}`);
        };
        document.body.appendChild(script);
    }
    
    // Expose widget state globally for the core scripts
    window.BookingWidget = widgetState;
    
    // Load CSS and initialize
    loadCSS();
    
    // If modal mode, create modal and set up button handler
    if (modalMode) {
        createModal();
        
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', setupModalButton);
        } else {
            setupModalButton();
        }
        
        function setupModalButton() {
            const openButton = document.getElementById('open-booking-modal');
            if (openButton) {
                openButton.addEventListener('click', function() {
                    // Initialize widget on first open
                    if (!widgetState.business) {
                        initWidget();
                    }
                    openModal();
                });
            }
        }
    } else {
        // Normal inline mode
        initWidget();
    }
    
})();
