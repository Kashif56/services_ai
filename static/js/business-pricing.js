/**
 * Business Pricing JavaScript for Services AI
 * Handles service management functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const addServiceForm = document.getElementById('addServiceForm');
    const deleteServiceForm = document.getElementById('deleteServiceForm');
    const deleteServiceId = document.getElementById('deleteServiceId');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    
    // Service icon preview
    const serviceIcon = document.getElementById('serviceIcon');
    const serviceColor = document.getElementById('serviceColor');
    
    if (serviceIcon && serviceColor) {
        // Create preview element if it doesn't exist
        if (!document.getElementById('iconPreview')) {
            const previewContainer = document.createElement('div');
            previewContainer.className = 'icon-preview-container mt-2';
            previewContainer.innerHTML = `
                <div class="service-icon" id="iconPreview" style="background-color: ${serviceColor.value}">
                    <i class="fas fa-${serviceIcon.value}"></i>
                </div>
            `;
            serviceIcon.parentNode.appendChild(previewContainer);
        }
        
        // Update preview when icon or color changes
        serviceIcon.addEventListener('change', updateIconPreview);
        serviceColor.addEventListener('input', updateIconPreview);
        
        // Initial preview
        updateIconPreview();
    }
    
    // Package functionality has been removed
    
    // Delete service confirmation
    const deleteServiceBtns = document.querySelectorAll('.delete-service-btn');
    if (deleteServiceBtns.length > 0) {
        deleteServiceBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const serviceId = this.getAttribute('data-service-id');
                if (serviceId && deleteServiceId) {
                    deleteServiceId.value = serviceId;
                    const deleteModal = new bootstrap.Modal(document.getElementById('deleteServiceModal'));
                    deleteModal.show();
                }
            });
        });
    }
    
    // Confirm delete
    if (confirmDeleteBtn && deleteServiceForm) {
        confirmDeleteBtn.addEventListener('click', function() {
            deleteServiceForm.submit();
        });
    }
    
    // Edit service functionality
    const editServiceBtns = document.querySelectorAll('.edit-service-btn');
    if (editServiceBtns.length > 0) {
        editServiceBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const serviceId = this.getAttribute('data-service-id');
                if (serviceId) {
                    // In a real implementation, you would fetch the service details
                    // and populate the form for editing
                    fetchServiceDetails(serviceId);
                }
            });
        });
    }
    
    // Bulk edit functionality
    const bulkEditBtn = document.getElementById('bulkEditBtn');
    if (bulkEditBtn) {
        bulkEditBtn.addEventListener('click', function(e) {
            e.preventDefault();
            // Toggle selection checkboxes for each row
            const servicesTable = document.getElementById('servicesTable');
            if (servicesTable) {
                const rows = servicesTable.querySelectorAll('tbody tr');
                
                // Check if we're already in bulk edit mode
                const isInBulkEditMode = servicesTable.classList.contains('bulk-edit-mode');
                
                if (isInBulkEditMode) {
                    // Exit bulk edit mode
                    servicesTable.classList.remove('bulk-edit-mode');
                    // Remove checkboxes
                    document.querySelectorAll('.bulk-select-cell').forEach(cell => {
                        cell.remove();
                    });
                    // Hide bulk actions
                    document.getElementById('bulkActionsContainer')?.remove();
                    // Update button text
                    this.innerHTML = '<i class="fas fa-edit me-2"></i>Bulk Edit';
                } else {
                    // Enter bulk edit mode
                    servicesTable.classList.add('bulk-edit-mode');
                    
                    // Add checkboxes to each row
                    rows.forEach(row => {
                        if (!row.querySelector('.bulk-select-cell')) {
                            const cell = document.createElement('td');
                            cell.className = 'bulk-select-cell';
                            cell.innerHTML = `
                                <div class="form-check">
                                    <input class="form-check-input bulk-select-check" type="checkbox" value="${row.getAttribute('data-service-id')}">
                                </div>
                            `;
                            row.insertBefore(cell, row.firstChild);
                        }
                    });
                    
                    // Add checkbox to header
                    const headerRow = servicesTable.querySelector('thead tr');
                    if (headerRow && !headerRow.querySelector('.bulk-select-cell')) {
                        const headerCell = document.createElement('th');
                        headerCell.className = 'bulk-select-cell';
                        headerCell.innerHTML = `
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="selectAllServices">
                            </div>
                        `;
                        headerRow.insertBefore(headerCell, headerRow.firstChild);
                        
                        // Select all functionality
                        document.getElementById('selectAllServices').addEventListener('change', function() {
                            document.querySelectorAll('.bulk-select-check').forEach(check => {
                                check.checked = this.checked;
                            });
                        });
                    }
                    
                    // Add bulk actions container
                    if (!document.getElementById('bulkActionsContainer')) {
                        const actionsContainer = document.createElement('div');
                        actionsContainer.id = 'bulkActionsContainer';
                        actionsContainer.className = 'bulk-actions-container mt-3';
                        actionsContainer.innerHTML = `
                            <div class="btn-group">
                                <button class="btn btn-sm btn-outline-primary" id="bulkActivateBtn">
                                    <i class="fas fa-check-circle me-1"></i>Activate
                                </button>
                                <button class="btn btn-sm btn-outline-secondary" id="bulkDeactivateBtn">
                                    <i class="fas fa-times-circle me-1"></i>Deactivate
                                </button>
                                <button class="btn btn-sm btn-outline-danger" id="bulkDeleteBtn">
                                    <i class="fas fa-trash-alt me-1"></i>Delete
                                </button>
                            </div>
                        `;
                        servicesTable.parentNode.appendChild(actionsContainer);
                        
                        // Bulk actions event listeners
                        document.getElementById('bulkActivateBtn').addEventListener('click', () => bulkAction('activate'));
                        document.getElementById('bulkDeactivateBtn').addEventListener('click', () => bulkAction('deactivate'));
                        document.getElementById('bulkDeleteBtn').addEventListener('click', () => bulkAction('delete'));
                    }
                    
                    // Update button text
                    this.innerHTML = '<i class="fas fa-times me-2"></i>Cancel Bulk Edit';
                }
            }
        });
    }
    
    // Helper Functions
    
    // Update icon preview
    function updateIconPreview() {
        const preview = document.getElementById('iconPreview');
        if (preview && serviceIcon && serviceColor) {
            preview.style.backgroundColor = serviceColor.value;
            preview.innerHTML = `<i class="fas fa-${serviceIcon.value}"></i>`;
        }
    }
    
    // Package functionality has been removed
    
    // Fetch service details for editing
    function fetchServiceDetails(serviceId) {
        // Show loading state
        const modal = new bootstrap.Modal(document.getElementById('addServiceModal'));
        modal.show();
        
        // Update modal title to indicate editing
        const modalTitle = document.getElementById('addServiceModalLabel');
        if (modalTitle) {
            modalTitle.textContent = 'Edit Service';
        }
        
        // Update form action to the correct update URL
        if (addServiceForm) {
            // Set the form action to the explicit update URL instead of string replacement
            addServiceForm.action = '/business/service/update/';
            
            // Add hidden service ID field
            if (!document.getElementById('editServiceId')) {
                const hiddenField = document.createElement('input');
                hiddenField.type = 'hidden';
                hiddenField.name = 'service_id';
                hiddenField.id = 'editServiceId';
                hiddenField.value = serviceId;
                addServiceForm.appendChild(hiddenField);
            } else {
                document.getElementById('editServiceId').value = serviceId;
            }
            
            // Fetch service details via AJAX
            fetch(`/business/service/${serviceId}/details/`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    // Populate form fields with service data
                    document.getElementById('serviceName').value = data.name;
                    document.getElementById('serviceDescription').value = data.description;
                    document.getElementById('servicePrice').value = data.price;
                    document.getElementById('serviceDuration').value = data.duration;
                    document.getElementById('serviceIcon').value = data.icon;
                    document.getElementById('serviceColor').value = data.color;
                    document.getElementById('serviceActive').checked = data.is_active;
                    
                    // Update icon preview
                    updateIconPreview();
                })
                .catch(error => {
                    console.error('Error fetching service details:', error);
                    alert('Error loading service details. Please try again.');
                });
        }
        
        // In a real implementation, you would populate the form with service data here
        // For now, we'll just show the modal
        modal.show();
    }
    
    // Perform bulk action
    function bulkAction(action) {
        const selectedServices = [];
        document.querySelectorAll('.bulk-select-check:checked').forEach(check => {
            selectedServices.push(check.value);
        });
        
        if (selectedServices.length === 0) {
            alert('Please select at least one service');
            return;
        }
        
        // In a real implementation, you would send this data to the server
        console.log(`Performing ${action} on services:`, selectedServices);
        
        // For demonstration, show a confirmation
        if (action === 'delete') {
            if (confirm(`Are you sure you want to delete ${selectedServices.length} service(s)?`)) {
                // Submit to server
                console.log('Confirmed delete');
            }
        } else {
            alert(`${selectedServices.length} service(s) will be ${action}d`);
        }
    }
});
