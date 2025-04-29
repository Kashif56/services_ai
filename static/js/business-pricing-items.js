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
    
    // Update price input based on price type
    if (priceType && priceValue && pricePrefix && priceSuffix) {
        priceType.addEventListener('change', function() {
            updatePriceInput(this.value, pricePrefix, priceSuffix);
        });
        
        // Set initial state
        updatePriceInput(priceType.value, pricePrefix, priceSuffix);
    }
    
    // Update edit form price input based on price type
    if (editPriceType && editPriceValue && editPricePrefix && editPriceSuffix) {
        editPriceType.addEventListener('change', function() {
            updatePriceInput(this.value, editPricePrefix, editPriceSuffix);
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
        switch(type) {
            case 'fixed':
                prefixElement.textContent = '$';
                suffixElement.textContent = '';
                break;
            case 'percentage':
                prefixElement.textContent = '';
                suffixElement.textContent = '%';
                break;
            case 'hourly':
                prefixElement.textContent = '$';
                suffixElement.textContent = '/hr';
                break;
            case 'per_unit':
                prefixElement.textContent = '$';
                suffixElement.textContent = '/unit';
                break;
            default:
                prefixElement.textContent = '$';
                suffixElement.textContent = '';
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
