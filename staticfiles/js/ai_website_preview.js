// AI Website Preview JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Handle iframe loading
    const iframes = document.querySelectorAll('.preview-iframe');
    
    iframes.forEach(function(iframe) {
        const container = iframe.closest('.iframe-container');
        
        // Add loading class
        container.classList.add('loading');
        
        iframe.addEventListener('load', function() {
            // Remove loading class when iframe loads
            container.classList.remove('loading');
            
            // Fade in animation
            iframe.style.opacity = '0';
            setTimeout(function() {
                iframe.style.transition = 'opacity 0.5s ease';
                iframe.style.opacity = '1';
            }, 100);
        });
        
        // Handle load errors
        iframe.addEventListener('error', function() {
            container.classList.remove('loading');
            container.innerHTML = '<div class="alert alert-danger m-4">Failed to load preview</div>';
        });
    });
    
    // Device tab switching
    const deviceTabs = document.querySelectorAll('#deviceTabs button[data-bs-toggle="tab"]');
    
    deviceTabs.forEach(function(tab) {
        tab.addEventListener('shown.bs.tab', function(event) {
            const targetId = event.target.getAttribute('data-bs-target');
            const targetPane = document.querySelector(targetId);
            
            if (targetPane) {
                const iframe = targetPane.querySelector('.preview-iframe');
                
                // Reload iframe if not already loaded
                if (iframe && !iframe.getAttribute('data-loaded')) {
                    iframe.setAttribute('data-loaded', 'true');
                }
            }
        });
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + 1 = Desktop view
        if ((e.ctrlKey || e.metaKey) && e.key === '1') {
            e.preventDefault();
            document.getElementById('desktop-tab').click();
        }
        
        // Ctrl/Cmd + 2 = Tablet view
        if ((e.ctrlKey || e.metaKey) && e.key === '2') {
            e.preventDefault();
            document.getElementById('tablet-tab').click();
        }
        
        // Ctrl/Cmd + 3 = Mobile view
        if ((e.ctrlKey || e.metaKey) && e.key === '3') {
            e.preventDefault();
            document.getElementById('mobile-tab').click();
        }
    });
    
    // Refresh button functionality
    const refreshBtn = document.getElementById('refreshPreview');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            const activePane = document.querySelector('.tab-pane.active');
            if (activePane) {
                const iframe = activePane.querySelector('.preview-iframe');
                if (iframe) {
                    // Add loading state
                    const container = iframe.closest('.iframe-container');
                    container.classList.add('loading');
                    
                    // Reload iframe
                    iframe.src = iframe.src;
                    
                    // Show feedback
                    const icon = this.querySelector('i');
                    icon.classList.add('fa-spin');
                    
                    setTimeout(function() {
                        icon.classList.remove('fa-spin');
                    }, 1000);
                }
            }
        });
    }
    
    // Fullscreen toggle
    const fullscreenBtn = document.getElementById('fullscreenToggle');
    if (fullscreenBtn) {
        fullscreenBtn.addEventListener('click', function() {
            const previewCard = document.querySelector('.preview-card');
            
            if (!document.fullscreenElement) {
                previewCard.requestFullscreen().catch(err => {
                    console.error('Error attempting to enable fullscreen:', err);
                });
            } else {
                document.exitFullscreen();
            }
        });
        
        // Update button icon on fullscreen change
        document.addEventListener('fullscreenchange', function() {
            const icon = fullscreenBtn.querySelector('i');
            if (document.fullscreenElement) {
                icon.classList.remove('fa-expand');
                icon.classList.add('fa-compress');
            } else {
                icon.classList.remove('fa-compress');
                icon.classList.add('fa-expand');
            }
        });
    }
    
    // Add smooth transitions when switching tabs
    const tabContent = document.getElementById('deviceTabContent');
    if (tabContent) {
        const tabPanes = tabContent.querySelectorAll('.tab-pane');
        
        tabPanes.forEach(function(pane) {
            pane.style.transition = 'opacity 0.3s ease';
        });
    }
    
    // Track time spent on preview
    let previewStartTime = Date.now();
    
    window.addEventListener('beforeunload', function() {
        const timeSpent = Math.floor((Date.now() - previewStartTime) / 1000);
        console.log('Time spent on preview:', timeSpent, 'seconds');
        // You can send this to analytics if needed
    });
});
