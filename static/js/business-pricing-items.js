/**
 * Business Pricing Items JavaScript for Services AI
 * Handles service item management functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const addServiceItemForm = document.getElementById('addServiceItemForm');
    const editServiceItemForm = document.getElementById('editServiceItemForm');
    const deleteServiceItemForm = document.getElementById('deleteServiceItemForm');
    const deleteItemId = document.getElementById('deleteItemId');
    const confirmDeleteItemBtn = document.getElementById('confirmDeleteItemBtn');
    
    // Price type handling
    const priceType = document.getElementById('priceType');
    const priceValue = document.getElementById('priceValue');
    const pricePrefix = document.getElementById('pricePrefix');
    const priceSuffix = document.getElementById('priceSuffix');
    
    // Edit form elements
    const editPriceType = document.getElementById('editPriceType');
    const editPriceValue = document.getElementById('editPriceValue');
    const editPricePrefix = document.getElementById('editPricePrefix');
    const editPriceSuffix = document.getElementById('editPriceSuffix');
    
    // Field type handling
    const fieldType = document.getElementById('fieldType');
    const fieldOptionsContainer = document.getElementById('fieldOptionsContainer');
    const fieldOptions = document.getElementById('fieldOptions');
    
    // Edit field type elements
    const editFieldType = document.getElementById('editFieldType');
    const editFieldOptionsContainer = document.getElementById('editFieldOptionsContainer');
    const editFieldOptions = document.getElementById('editFieldOptions');
    
    // Update price input based on price type
    if (priceType && priceValue && pricePrefix && priceSuffix) {
        priceType.addEventListener('change', function() {
            updatePriceInput(this.value, pricePrefix, priceSuffix);
            
            // Update field type based on price type
            if (fieldType) {
                if (this.value === 'free') {
                    // Enable field type selection for free items
                    fieldType.disabled = false;
                    document.querySelector('label[for="fieldType"]').classList.remove('text-muted');
                } else {
                    // Force number field type for non-free items
                    fieldType.value = 'number';
                    fieldType.disabled = true;
                    document.querySelector('label[for="fieldType"]').classList.add('text-muted');
                    
                    // Update field options visibility
                    if (fieldOptionsContainer) {
                        updateFieldOptionsVisibility('number', fieldOptionsContainer);
                    }
                }
            }
        });
        
        // Set initial state
        updatePriceInput(priceType.value, pricePrefix, priceSuffix);
        
        // Set initial field type state based on price type
        if (fieldType) {
            if (priceType.value === 'free') {
                fieldType.disabled = false;
                document.querySelector('label[for="fieldType"]').classList.remove('text-muted');
            } else {
                fieldType.value = 'number';
                fieldType.disabled = true;
                document.querySelector('label[for="fieldType"]').classList.add('text-muted');
                
                // Update field options visibility
                if (fieldOptionsContainer) {
                    updateFieldOptionsVisibility('number', fieldOptionsContainer);
                }
            }
        }
    }
    
    // Update edit form price input based on price type
    if (editPriceType && editPriceValue && editPricePrefix && editPriceSuffix) {
        editPriceType.addEventListener('change', function() {
            updatePriceInput(this.value, editPricePrefix, editPriceSuffix);
            
            // Update field type based on price type
            if (editFieldType) {
                if (this.value === 'free') {
                    // Enable field type selection for free items
                    editFieldType.disabled = false;
                    document.querySelector('label[for="editFieldType"]').classList.remove('text-muted');
                } else {
                    // Force number field type for non-free items
                    editFieldType.value = 'number';
                    editFieldType.disabled = true;
                    document.querySelector('label[for="editFieldType"]').classList.add('text-muted');
                    
                    // Update field options visibility
                    if (editFieldOptionsContainer) {
                        updateFieldOptionsVisibility('number', editFieldOptionsContainer);
                    }
                }
            }
        });
    }
    
    // Handle field type changes in add form
    if (fieldType && fieldOptionsContainer) {
        fieldType.addEventListener('change', function() {
            updateFieldOptionsVisibility(this.value, fieldOptionsContainer);
        });
        
        // Set initial state
        updateFieldOptionsVisibility(fieldType.value, fieldOptionsContainer);
    }
    
    // Handle field type changes in edit form
    if (editFieldType && editFieldOptionsContainer) {
        editFieldType.addEventListener('change', function() {
            updateFieldOptionsVisibility(this.value, editFieldOptionsContainer);
        });
    }
    
    // Delete service item confirmation
    const deleteItemBtns = document.querySelectorAll('.delete-item-btn');
    if (deleteItemBtns.length > 0) {
        deleteItemBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const itemId = this.getAttribute('data-item-id');
                if (itemId && deleteItemId) {
                    deleteItemId.value = itemId;
                    const deleteModal = new bootstrap.Modal(document.getElementById('deleteServiceItemModal'));
                    deleteModal.show();
                }
            });
        });
    }
    
    // Confirm delete
    if (confirmDeleteItemBtn && deleteServiceItemForm) {
        confirmDeleteItemBtn.addEventListener('click', function() {
            deleteServiceItemForm.submit();
        });
    }
    
    // Edit service item functionality
    const editItemBtns = document.querySelectorAll('.edit-item-btn');
    if (editItemBtns.length > 0) {
        editItemBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const itemId = this.getAttribute('data-item-id');
                if (itemId) {
                    fetchServiceItemDetails(itemId);
                }
            });
        });
    }
    
    // Helper Functions
    
    /**
     * Update price input based on price type
     */
    function updatePriceInput(type, prefixElement, suffixElement) {
        // Get the price value input element
        const priceValueInput = prefixElement.parentElement.querySelector('input');
        
        // Handle different price types
        switch(type) {
            case 'fixed':
                prefixElement.textContent = '$';
                suffixElement.textContent = '';
                priceValueInput.disabled = false;
                priceValueInput.required = true;
                priceValueInput.parentElement.style.display = 'flex';
                break;
            case 'percentage':
                prefixElement.textContent = '';
                suffixElement.textContent = '%';
                priceValueInput.disabled = false;
                priceValueInput.required = true;
                priceValueInput.parentElement.style.display = 'flex';
                break;
            case 'hourly':
                prefixElement.textContent = '$';
                suffixElement.textContent = '/hr';
                priceValueInput.disabled = false;
                priceValueInput.required = true;
                priceValueInput.parentElement.style.display = 'flex';
                break;
            case 'per_unit':
                prefixElement.textContent = '$';
                suffixElement.textContent = '/unit';
                priceValueInput.disabled = false;
                priceValueInput.required = true;
                priceValueInput.parentElement.style.display = 'flex';
                break;
            case 'free':
                // For free items, hide the price value input and set it to 0
                priceValueInput.value = '0';
                priceValueInput.disabled = true;
                priceValueInput.required = false;
                // Optional: Hide the entire price value input group
                // priceValueInput.parentElement.style.display = 'none';
                break;
            default:
                prefixElement.textContent = '$';
                suffixElement.textContent = '';
                priceValueInput.disabled = false;
                priceValueInput.required = true;
                priceValueInput.parentElement.style.display = 'flex';
        }
    }
    
    /**
     * Update field options visibility based on field type
     */
    function updateFieldOptionsVisibility(fieldType, optionsContainer) {
        // Only show options for select field type
        if (fieldType === 'select') {
            optionsContainer.style.display = 'block';
            const optionsInput = optionsContainer.querySelector('input');
            if (optionsInput) {
                optionsInput.required = true;
            }
        } else {
            optionsContainer.style.display = 'none';
            const optionsInput = optionsContainer.querySelector('input');
            if (optionsInput) {
                optionsInput.required = false;
            }
        }
    }
    
    /**
     * Fetch service item details for editing
     */
    function fetchServiceItemDetails(itemId) {
        // In a real implementation, this would make an AJAX call to get the item details
        // For now, we'll simulate this with a fetch request
        
        fetch(`/business/api/service-items/${itemId}/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Populate the edit form
                document.getElementById('editItemId').value = data.id;
                document.getElementById('editItemName').value = data.name;
                document.getElementById('editItemDescription').value = data.description || '';
                document.getElementById('editPriceType').value = data.price_type;
                document.getElementById('editPriceValue').value = data.price_value;
                document.getElementById('editDurationMinutes').value = data.duration_minutes;
                document.getElementById('editMaxQuantity').value = data.max_quantity;
                document.getElementById('editItemOptional').checked = data.is_optional;
                document.getElementById('editItemActive').checked = data.is_active;
                
                // Set field type and options
                if (data.field_type) {
                    document.getElementById('editFieldType').value = data.field_type;
                }
                
                // Handle field options for select type
                if (data.field_options && Array.isArray(data.field_options)) {
                    document.getElementById('editFieldOptions').value = data.field_options.join(', ');
                } else if (data.field_options && typeof data.field_options === 'string') {
                    document.getElementById('editFieldOptions').value = data.field_options;
                }
                
                // Update field options visibility
                updateFieldOptionsVisibility(data.field_type || 'text', editFieldOptionsContainer);
                
                // Set field type state based on price type
                if (data.price_type === 'free') {
                    // Enable field type selection for free items
                    document.getElementById('editFieldType').disabled = false;
                    document.querySelector('label[for="editFieldType"]').classList.remove('text-muted');
                } else {
                    // Force number field type for non-free items
                    document.getElementById('editFieldType').value = 'number';
                    document.getElementById('editFieldType').disabled = true;
                    document.querySelector('label[for="editFieldType"]').classList.add('text-muted');
                }
                
                // Update price input display
                updatePriceInput(data.price_type, editPricePrefix, editPriceSuffix);
                
                // Show the modal
                const editModal = new bootstrap.Modal(document.getElementById('editServiceItemModal'));
                editModal.show();
            })
            .catch(error => {
                console.error('Error fetching service item details:', error);
                alert('Failed to load service item details. Please try again.');
            });
    }
});
