// Leads Index JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize any tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Date range filter handling
    const dateFrom = document.getElementById('date_from');
    const dateTo = document.getElementById('date_to');
    
    if (dateFrom && dateTo) {
        dateFrom.addEventListener('change', function() {
            // If the "to" date is earlier than the "from" date, update it
            if (dateTo.value && dateFrom.value > dateTo.value) {
                dateTo.value = dateFrom.value;
            }
        });
        
        dateTo.addEventListener('change', function() {
            // If the "from" date is later than the "to" date, update it
            if (dateFrom.value && dateTo.value < dateFrom.value) {
                dateFrom.value = dateTo.value;
            }
        });
    }

    // Handle filter form submission
    const filterForm = document.getElementById('lead-filter-form');
    if (filterForm) {
        filterForm.addEventListener('submit', function(event) {
            // Remove empty parameters to keep the URL clean
            const formElements = Array.from(filterForm.elements);
            formElements.forEach(element => {
                if (element.value === '' && element.name) {
                    element.disabled = true;
                }
            });
            
            // Form will submit normally with only non-empty parameters
        });
    }
});
