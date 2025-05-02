/**
 * Dashboard JavaScript for Services AI
 * Handles sidebar toggle, notifications, and other dashboard interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Sidebar toggle functionality
    const sidebarToggle = document.getElementById('sidebarCollapse');
    const sidebarToggleSmall = document.getElementById('sidebarCollapseSmall');
    const sidebar = document.getElementById('sidebar');
    
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            document.body.classList.toggle('sidebar-collapsed');
            
            // Save sidebar state to localStorage
            if (document.body.classList.contains('sidebar-collapsed')) {
                localStorage.setItem('sidebar-collapsed', 'true');
            } else {
                localStorage.setItem('sidebar-collapsed', 'false');
            }
        });
    }
    
    if (sidebarToggleSmall) {
        try {
            sidebarToggleSmall.addEventListener('click', function() {
                document.body.classList.remove('sidebar-mobile-open');
            });
        } catch (error) {
            console.error('Error adding event listener to sidebarToggleSmall:', error);
        }
    }
    
    // Check for saved sidebar state
    if (localStorage.getItem('sidebar-collapsed') === 'true') {
        document.body.classList.add('sidebar-collapsed');
    }
    
    // Mobile sidebar toggle
    const navbarToggler = document.querySelector('.navbar-toggler');
    if (navbarToggler) {
        navbarToggler.addEventListener('click', function() {
            document.body.classList.toggle('sidebar-mobile-open');
        });
    }
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(event) {
        // Make sure sidebar exists before trying to use it
        if (!sidebar) return;
        
        const isClickInsideSidebar = sidebar.contains(event.target);
        const isClickOnToggler = navbarToggler ? navbarToggler.contains(event.target) : false;
        
        if (!isClickInsideSidebar && !isClickOnToggler && window.innerWidth < 992) {
            if (document.body.classList.contains('sidebar-mobile-open')) {
                document.body.classList.remove('sidebar-mobile-open');
            }
        }
    });
    
    // Responsive adjustments on window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth >= 992) {
            document.body.classList.remove('sidebar-mobile-open');
        }
    });
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Toast notifications
    const toastElList = [].slice.call(document.querySelectorAll('.toast'));
    toastElList.map(function(toastEl) {
        return new bootstrap.Toast(toastEl, {
            autohide: true,
            delay: 5000
        }).show();
    });
    
    // Dropdown menus - prevent closing when clicking inside
    document.querySelectorAll('.dropdown-menu.keep-open').forEach(function(element) {
        element.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    });
});
