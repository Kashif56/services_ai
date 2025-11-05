/**
 * Plugin Notification System
 * Listens for SSE events and displays toast notifications
 */

(function() {
    'use strict';

    // Check if user is authenticated
    const userId = document.body.dataset.userId;
    if (!userId) {
        return;
    }

    // Check for pending notifications from localStorage (after page redirect)
    checkPendingNotifications();

    // Create EventSource connection
    const eventSource = new EventSource(`/events/user-${userId}/`);

    // Listen for 'message' events (this is what we send from backend)
    eventSource.addEventListener('message', function(e) {
        // Skip empty keep-alive messages
        if (!e.data || e.data.trim() === '') {
            return;
        }
        
        try {
            const data = JSON.parse(e.data);
            
            // Save to localStorage first (in case page redirects)
            saveNotificationForLater(data);
            
            // Also try to show immediately
            showNotification(data);
        } catch (error) {
            console.error('[Notifications] Error parsing event data:', error);
        }
    });
    
    // Handle errors
    eventSource.addEventListener('error', function(e) {
        if (eventSource.readyState === EventSource.CLOSED) {
            console.error('[Notifications] SSE connection closed');
        }
    });

    /**
     * Check for pending notifications in localStorage
     */
    function checkPendingNotifications() {
        try {
            const pendingNotifications = localStorage.getItem('pendingNotifications');
            if (pendingNotifications) {
                const notifications = JSON.parse(pendingNotifications);
                
                // Clear from localStorage
                localStorage.removeItem('pendingNotifications');
                
                // Show each notification
                notifications.forEach(notification => {
                    // Small delay to ensure DOM is ready
                    setTimeout(() => showNotification(notification), 100);
                });
            }
        } catch (error) {
            console.error('[Notifications] Error checking pending notifications:', error);
        }
    }

    /**
     * Save notification to localStorage for display after redirect
     */
    function saveNotificationForLater(data) {
        try {
            let pending = [];
            const existing = localStorage.getItem('pendingNotifications');
            if (existing) {
                pending = JSON.parse(existing);
            }
            
            pending.push(data);
            localStorage.setItem('pendingNotifications', JSON.stringify(pending));
        } catch (error) {
            console.error('[Notifications] Error saving notification:', error);
        }
    }

    /**
     * Display a notification
     */
    function showNotification(data, saveForLater = false) {
        // If saveForLater is true, store in localStorage instead of showing immediately
        if (saveForLater) {
            saveNotificationForLater(data);
            return;
        }
        
        const message = data.message || 'Notification';
        const type = data.type || 'info';
        const plugin = data.plugin || 'Plugin';

        // Try to use Bootstrap toast if available
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            showBootstrapToast(message, type, plugin);
        } 
        // Try to use browser notification API
        else if ('Notification' in window && Notification.permission === 'granted') {
            showBrowserNotification(message, type, plugin);
        }
        // Fallback to alert
        else {
            alert(`[${plugin}] ${message}`);
        }
    }

    /**
     * Show Bootstrap toast notification
     */
    function showBootstrapToast(message, type, plugin) {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }

        // Map notification types to Bootstrap classes
        const typeMap = {
            'success': 'bg-success text-white',
            'error': 'bg-danger text-white',
            'warning': 'bg-warning text-dark',
            'info': 'bg-info text-white'
        };
        const bgClass = typeMap[type] || 'bg-primary text-white';

        // Create toast element
        const toastId = 'toast-' + Date.now();
        const toastHtml = `
            <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header ${bgClass}">
                    <i class="fas fa-bell me-2"></i>
                    <strong class="me-auto">${escapeHtml(plugin)}</strong>
                    <small>Just now</small>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${escapeHtml(message)}
                </div>
            </div>
        `;

        toastContainer.insertAdjacentHTML('beforeend', toastHtml);

        // Show the toast
        const toastElement = document.getElementById(toastId);
        
        if (!toastElement) {
            return;
        }
        
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: 5000
        });
        
        toast.show();

        // Remove toast element after it's hidden
        toastElement.addEventListener('hidden.bs.toast', function() {
            toastElement.remove();
        });
    }

    /**
     * Show browser notification
     */
    function showBrowserNotification(message, type, plugin) {
        const notification = new Notification(plugin, {
            body: message,
            icon: '/static/images/notification-icon.png', // Update with your icon path
            badge: '/static/images/badge-icon.png'
        });

        notification.onclick = function() {
            window.focus();
            notification.close();
        };
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Request notification permission (optional)
     */
    function requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().then(function(permission) {
                console.log('[Notifications] Permission:', permission);
            });
        }
    }

    // Optionally request notification permission on page load
    // requestNotificationPermission();

})();
