// Staff Detail Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Handle tab navigation with URL hash
    const handleTabHash = function() {
        const hash = window.location.hash;
        if (hash) {
            // Find the tab button with matching data-bs-target
            const tabButton = document.querySelector(`button[data-bs-target="${hash}"]`);
            if (tabButton) {
                // Trigger Bootstrap tab
                const tab = new bootstrap.Tab(tabButton);
                tab.show();
            }
        }
    };
    
    // Handle hash on page load
    handleTabHash();
    
    // Add hash to URL when tab is clicked
    const tabButtons = document.querySelectorAll('button[data-bs-toggle="tab"]');
    tabButtons.forEach(button => {
        button.addEventListener('shown.bs.tab', function(event) {
            // Get the target tab pane id
            const targetId = event.target.getAttribute('data-bs-target');
            if (targetId) {
                // Update URL hash without scrolling
                history.replaceState(null, null, targetId);
            }
        });
    });
    
    // Handle browser back/forward buttons
    window.addEventListener('hashchange', handleTabHash);
    
    // Edit profile functionality
    const editStaffBtn = document.getElementById('editStaffBtn');
    const cancelEditBtn = document.getElementById('cancelEditBtn');
    const staffProfileForm = document.getElementById('staffProfileForm');
    const formInputs = staffProfileForm.querySelectorAll('input, textarea, select');
    const formActions = staffProfileForm.querySelector('.form-actions');
    const avatarUploadOverlay = document.getElementById('avatarUploadOverlay');
    
    if (editStaffBtn) {
        editStaffBtn.addEventListener('click', function() {
            // Enable all form inputs
            formInputs.forEach(input => {
                input.disabled = false;
            });
            
            // Show form actions and avatar upload overlay
            formActions.classList.remove('d-none');
            avatarUploadOverlay.classList.remove('d-none');
            
            // Hide edit button
            editStaffBtn.classList.add('d-none');
        });
    }
    
    if (cancelEditBtn) {
        cancelEditBtn.addEventListener('click', function() {
            // Disable all form inputs
            formInputs.forEach(input => {
                input.disabled = true;
            });
            
            // Hide form actions and avatar upload overlay
            formActions.classList.add('d-none');
            avatarUploadOverlay.classList.add('d-none');
            
            // Show edit button
            editStaffBtn.classList.remove('d-none');
            
            // Reset form to original values
            staffProfileForm.reset();
        });
    }
    
    // Avatar image preview
    const avatarUpload = document.getElementById('avatarUpload');
    const avatarPreview = document.getElementById('avatarPreview');
    
    if (avatarUpload && avatarPreview) {
        avatarUpload.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    // Check if avatarPreview is an img or div
                    if (avatarPreview.tagName === 'IMG') {
                        avatarPreview.src = e.target.result;
                    } else {
                        // Create new img element
                        const img = document.createElement('img');
                        img.src = e.target.result;
                        img.className = 'staff-avatar';
                        img.id = 'avatarPreview';
                        
                        // Replace placeholder with img
                        avatarPreview.parentNode.replaceChild(img, avatarPreview);
                    }
                };
                
                reader.readAsDataURL(this.files[0]);
            }
        });
    }
    
    // Handle off day checkbox to make time fields optional
    const offDayCheckbox = document.getElementById('offDay');
    const startTimeField = document.getElementById('startTime');
    const endTimeField = document.getElementById('endTime');
    
    if (offDayCheckbox && startTimeField && endTimeField) {
        offDayCheckbox.addEventListener('change', function() {
            if (this.checked) {
                // If marked as off day, make time fields optional
                startTimeField.required = false;
                endTimeField.required = false;
                
                // Set default times if empty (midnight to 11:59 PM)
                if (!startTimeField.value) startTimeField.value = '00:00';
                if (!endTimeField.value) endTimeField.value = '23:59';
                
                // Add disabled appearance but don't actually disable
                // so the values still get submitted
                startTimeField.classList.add('text-muted');
                endTimeField.classList.add('text-muted');
            } else {
                // If not off day, make time fields required again
                startTimeField.required = true;
                endTimeField.required = true;
                startTimeField.classList.remove('text-muted');
                endTimeField.classList.remove('text-muted');
            }
        });
    }
    
    // Same for edit modal
    const editOffDayCheckbox = document.getElementById('editOffDay');
    const editStartTimeField = document.getElementById('editStartTime');
    const editEndTimeField = document.getElementById('editEndTime');
    
    if (editOffDayCheckbox && editStartTimeField && editEndTimeField) {
        editOffDayCheckbox.addEventListener('change', function() {
            if (this.checked) {
                // If marked as off day, make time fields optional
                editStartTimeField.required = false;
                editEndTimeField.required = false;
                
                // Set default times if empty (midnight to 11:59 PM)
                if (!editStartTimeField.value) editStartTimeField.value = '00:00';
                if (!editEndTimeField.value) editEndTimeField.value = '23:59';
                
                // Add disabled appearance but don't actually disable
                editStartTimeField.classList.add('text-muted');
                editEndTimeField.classList.add('text-muted');
            } else {
                // If not off day, make time fields required again
                editStartTimeField.required = true;
                editEndTimeField.required = true;
                editStartTimeField.classList.remove('text-muted');
                editEndTimeField.classList.remove('text-muted');
            }
        });
    }
    
    // Add weekday availability buttons
    const addWeekdayButtons = document.querySelectorAll('.add-weekday-availability');
    const addAvailabilityModal = document.getElementById('addAvailabilityModal');
    const addAvailabilityForm = document.getElementById('addAvailabilityForm');
    const availabilityType = document.getElementById('availabilityType');
    const weeklyFields = document.getElementById('weeklyFields');
    const specificFields = document.getElementById('specificFields');
    const weekdayInput = document.getElementById('weekday');
    const weekdayDisplayInput = document.getElementById('weekdayDisplay');
    const fromDateInput = document.getElementById('fromDate');
    const toDateInput = document.getElementById('toDate');
    const addModalTitle = document.getElementById('addAvailabilityModalLabel');
    
    // Initialize Bootstrap modal instance
    let addModalInstance = null;
    if (addAvailabilityModal) {
        addModalInstance = new bootstrap.Modal(addAvailabilityModal);
    }
    
    if (addWeekdayButtons.length && addModalInstance) {
        addWeekdayButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const weekdayNum = this.dataset.weekday;
                const weekdayName = this.dataset.weekdayName;
                
                // Set modal title
                addModalTitle.textContent = `Add Availability for ${weekdayName}`;
                
                // Set availability type to weekly
                availabilityType.value = 'weekly';
                
                // Show weekly fields, hide specific fields
                weeklyFields.style.display = 'block';
                specificFields.style.display = 'none';
                
                // Set weekday values
                weekdayInput.value = weekdayNum;
                weekdayDisplayInput.value = weekdayName;
                
                // Make date fields not required for weekly, time fields required
                if (fromDateInput) fromDateInput.required = false;
                if (toDateInput) toDateInput.required = false;
                const startTimeField = document.getElementById('startTime');
                const endTimeField = document.getElementById('endTime');
                if (startTimeField) startTimeField.required = true;
                if (endTimeField) endTimeField.required = true;
                
                // Reset form
                addAvailabilityForm.reset();
                availabilityType.value = 'weekly';
                weekdayInput.value = weekdayNum;
                weekdayDisplayInput.value = weekdayName;
                
                // Show modal
                addModalInstance.show();
            });
        });
    }
    
    // Reset modal when adding specific date from header button
    const addSpecificDateBtns = document.querySelectorAll('[data-bs-target="#addAvailabilityModal"]');
    if (addSpecificDateBtns.length && addModalInstance) {
        addSpecificDateBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                // Reset modal title
                addModalTitle.textContent = 'Add Holiday/Off Day';
                
                // Set availability type to specific
                availabilityType.value = 'specific';
                
                // Show specific fields, hide weekly fields
                weeklyFields.style.display = 'none';
                specificFields.style.display = 'block';
                
                // Make from_date and to_date required, time fields not required
                if (fromDateInput) fromDateInput.required = true;
                if (toDateInput) toDateInput.required = true;
                const startTimeField = document.getElementById('startTime');
                const endTimeField = document.getElementById('endTime');
                if (startTimeField) startTimeField.required = false;
                if (endTimeField) endTimeField.required = false;
                
                // Reset form
                addAvailabilityForm.reset();
                availabilityType.value = 'specific';
            });
        });
    }
    
    // Edit availability modal
    const editAvailabilityButtons = document.querySelectorAll('.edit-availability');
    const editAvailabilityModal = document.getElementById('editAvailabilityModal');
    const editAvailabilityForm = document.getElementById('editAvailabilityForm');
    const editAvailId = document.getElementById('editAvailId');
    const editSpecificDate = document.getElementById('editSpecificDate');
    const editStartTime = document.getElementById('editStartTime');
    const editEndTime = document.getElementById('editEndTime');
    const editOffDay = document.getElementById('editOffDay');
    const editWeekday = document.getElementById('editWeekday');
    const editWeekdayDisplay = document.getElementById('editWeekdayDisplay');
    const editWeeklyFields = document.getElementById('editWeeklyFields');
    const editSpecificFields = document.getElementById('editSpecificFields');
    
    // Initialize Bootstrap modal instance for edit modal
    let editModalInstance = null;
    if (editAvailabilityModal) {
        editModalInstance = new bootstrap.Modal(editAvailabilityModal);
    }
    
    if (editAvailabilityButtons.length && editModalInstance) {
        editAvailabilityButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const availId = this.dataset.availId;
                const availType = this.dataset.availType;
                
                // Set form values
                editAvailId.value = availId;
                
                const editWeeklyTimeFields = document.getElementById('editWeeklyTimeFields');
                
                // Determine which fields to show based on availability type
                if (availType === 'weekly') {
                    editWeeklyFields.style.display = 'block';
                    editSpecificFields.style.display = 'none';
                    editWeeklyTimeFields.style.display = 'block';
                    
                    // Set weekday display and hidden value
                    const weekdayNum = this.dataset.weekday;
                    const weekdayName = getWeekdayName(weekdayNum);
                    editWeekday.value = weekdayNum;
                    editWeekdayDisplay.value = weekdayName;
                    
                    editStartTime.value = this.dataset.startTime;
                    editEndTime.value = this.dataset.endTime;
                    editOffDay.checked = this.dataset.offDay === 'true';
                    
                    // Trigger the change event to update required fields
                    if (editOffDay.checked) {
                        const event = new Event('change');
                        editOffDay.dispatchEvent(event);
                    }
                } else {
                    // Specific date (holiday)
                    editWeeklyFields.style.display = 'none';
                    editSpecificFields.style.display = 'block';
                    editWeeklyTimeFields.style.display = 'none';
                    
                    editSpecificDate.value = this.dataset.specificDate;
                    
                    // Set notes if available
                    const editNotes = document.getElementById('editNotes');
                    if (editNotes && this.dataset.notes) {
                        editNotes.value = this.dataset.notes;
                    }
                }
                
                // Show modal using Bootstrap
                editModalInstance.show();
            });
        });
    }
    
    // Helper function to get weekday name from number
    function getWeekdayName(weekdayNum) {
        const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        return weekdays[parseInt(weekdayNum)];
    }
    
    // Delete availability
    const deleteAvailabilityButtons = document.querySelectorAll('.delete-availability');
    
    if (deleteAvailabilityButtons.length) {
        deleteAvailabilityButtons.forEach(button => {
            button.addEventListener('click', function() {
                const availId = this.dataset.availId;
                
                if (confirm('Are you sure you want to delete this availability?')) {
                    // Send AJAX request to delete availability
                    fetch('/business/staff/delete/availability/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: JSON.stringify({
                            availability_id: availId
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Show success message
                            showToast('Availability deleted successfully', 'success');
                            // Reload page to update availability list
                            window.location.reload();
                        } else {
                            // Show error message
                            showToast('Error deleting availability: ' + data.message, 'error');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        showToast('An error occurred while deleting availability', 'error');
                    });
                }
            });
        });
    }
    
    // Function to get CSRF token from cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Edit service assignment modal
    const editServiceAssignmentButtons = document.querySelectorAll('.edit-service-assignment');
    const editServiceAssignmentModal = document.getElementById('editServiceAssignmentModal');
    const editServiceAssignmentForm = document.getElementById('editServiceAssignmentForm');
    const editAssignmentId = document.getElementById('editAssignmentId');
    const editIsPrimary = document.getElementById('editIsPrimary');
    
    // Initialize Bootstrap modal instance for edit service assignment
    let editServiceAssignmentModalInstance = null;
    if (editServiceAssignmentModal) {
        editServiceAssignmentModalInstance = new bootstrap.Modal(editServiceAssignmentModal);
    }
    
    if (editServiceAssignmentButtons.length && editServiceAssignmentModalInstance) {
        editServiceAssignmentButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const assignmentId = this.dataset.assignmentId;
                const serviceId = this.dataset.serviceId;
                const isPrimary = this.dataset.isPrimary === 'true';
                
                // Set form values
                editAssignmentId.value = assignmentId;
                
                // Select the correct radio button
                const radioButton = document.getElementById(`edit_service_${serviceId}`);
                if (radioButton) {
                    radioButton.checked = true;
                }
                
                editIsPrimary.checked = isPrimary;
                
                // Show modal
                editServiceAssignmentModalInstance.show();
            });
        });
    }
    
    // Delete service assignment
    const deleteServiceAssignmentButtons = document.querySelectorAll('.delete-service-assignment');
    
    if (deleteServiceAssignmentButtons.length) {
        deleteServiceAssignmentButtons.forEach(button => {
            button.addEventListener('click', function() {
                const assignmentId = this.dataset.assignmentId;
                console.log(this.dataset);
                
                console.log("Assignment Id: ", assignmentId)
                
                if (confirm('Are you sure you want to remove this service assignment?')) {
                    // Send AJAX request to delete service assignment
                    fetch('/business/staff/delete/service-assignment/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: JSON.stringify({
                            assignment_id: assignmentId
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Show success message
                            showToast('Service assignment removed successfully', 'success');
                            // Reload page to update assignment list
                            window.location.reload();
                        } else {
                            // Show error message
                            showToast('Error removing service assignment: ' + data.message, 'error');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        showToast('An error occurred while removing service assignment', 'error');
                    });
                }
            });
        });
    }
    
    // Function to show toast notifications
    function showToast(message, type = 'info') {
        // Check if Bootstrap toast is available
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            // Create toast element
            const toastEl = document.createElement('div');
            toastEl.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
            toastEl.setAttribute('role', 'alert');
            toastEl.setAttribute('aria-live', 'assertive');
            toastEl.setAttribute('aria-atomic', 'true');
            
            toastEl.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            `;
            
            // Add to container or body
            let toastContainer = document.querySelector('.toast-container');
            if (!toastContainer) {
                toastContainer = document.createElement('div');
                toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
                document.body.appendChild(toastContainer);
            }
            
            toastContainer.appendChild(toastEl);
            
            // Initialize and show toast
            const toast = new bootstrap.Toast(toastEl, {
                autohide: true,
                delay: 5000
            });
            toast.show();
            
            // Remove toast element after it's hidden
            toastEl.addEventListener('hidden.bs.toast', function() {
                toastEl.remove();
            });
        } else {
            // Fallback to alert if Bootstrap is not available
            if (type === 'error') {
                alert('Error: ' + message);
            } else {
                alert(message);
            }
        }
    }
});
